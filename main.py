import requests
import re
import json
from multiprocessing.pool import ThreadPool
from ua import random_agent
import time


class skyScraper():

    @staticmethod
    def range_gen(month, year, trip_days, to_airpot, from_airport):
        ranges = []
        for i in range(1, 28 - trip_days):
            j = i + trip_days
            f = "0{}".format(i) if i < 10 else "{}".format(i)
            t = "0{}".format(j) if j < 10 else str(j)
            from_date = "{}-{}-{}".format(year, month, f)
            to_date = "{}-{}-{}".format(year, month, t)
            ranges.append([from_date, to_date, to_airpot, from_airport])
        return ranges

    @staticmethod
    def find_in_range(month, year, trip_days, to_airpot, from_airport="tlv"):
        ranges = []
        if month < 10:
            month = "0{}".format(month)
        for trip_day in trip_days:
            ranges.extend(skyScraper.range_gen(month, year, trip_day, to_airpot, from_airport))
        tp = ThreadPool(10)
        results = tp.map(lambda x: skyScraper(*x).scrape(), ranges)
        tp.close()
        tp.join()
        return zip(ranges, results)

    #         for i in ranges:
    #             try:
    #                 print(skyScraper(*i).scrape())
    #             except Exception as e:
    #                 print(i)
    # return [x["price"]["amount"] for x in filter(lambda x: x, results)]

    GOOD_CALL = {"market": "IL", "currency": "USD", "locale": "en-US", "cabin_class": "economy", "prefer_directs": True,
                 "trip_type": "return", "legs": [
            {"origin": "CAI", "destination": "NYCA", "date": "2019-07-02", "return_date": "2020-02-10",
             "add_alternative_origins": False, "add_alternative_destinations": False}],
                 "origin": {"id": "CAI", "airportId": "CAI", "name": "Cairo", "cityId": "CAIR", "cityName": "Cairo",
                            "countryId": "EG", "type": "Airport", "centroidCoordinates": [31.406944, 30.1375]},
                 "destination": {"id": "NYCA", "name": "New York", "cityId": "NYCA", "cityName": "New York",
                                 "countryId": "US", "type": "City",
                                 "centroidCoordinates": [-73.9282670243, 40.6940959901]}, "outboundDate": "2019-07-02",
                 "inboundDate": "2020-02-10", "adults": 1, "child_ages": [],
                 "options": {"include_unpriced_itineraries": True, "include_mixed_booking_options": True},
                 "trusted_funnel_search_guid": "NVM", "state": {}}

    def __init__(self, from_date, to_date, to_airport, from_airport="TLV"):
        self.from_date = from_date
        self.to_date = to_date
        self.to_airport = to_airport
        self.from_airport = from_airport

    def scrape(self):
        resp = self.first_call()
        payload = self.prepare_payload(resp)
        time.sleep(3)
        tries = 0
        while tries < 5:
            resp = self.second_call(payload)
            best = self.best_offer(resp)
            if best:
                return best
            tries += 1
        return

    def prepare_payload(self, parsed_payload):
        TEMPLATE_CALL = {"options":
                             {"include_unpriced_itineraries": True, "include_mixed_booking_options": True},
                         "cabin_class": "economy", "prefer_directs": False, "state": {}, "child_ages": [],
                         "trip_type": "return", "adults": 1}
        GOOD_CALL = {"market": "IL", "currency": "USD",
                     "locale": "en-US", "cabin_class": "economy",
                     "prefer_directs": False, "trip_type": "return",
                     "legs": [
                         {"origin": "CAI", "destination": "NYCA", "date": "2019-07-02", "return_date": "2020-02-10",
                          "add_alternative_origins": False, "add_alternative_destinations": False}],
                     "origin": {"id": "CAI", "airportId": "CAI", "name": "Cairo", "cityId": "CAIR", "cityName": "Cairo",
                                "countryId": "EG", "type": "Airport", "centroidCoordinates": [31.406944, 30.1375]},
                     "destination": {"id": "NYCA", "name": "New York", "cityId": "NYCA", "cityName": "New York",
                                     "countryId": "US", "type": "City",
                                     "centroidCoordinates": [-73.9282670243, 40.6940959901]},
                     "outboundDate": "2019-07-02", "inboundDate": "2020-02-10", "adults": 1, "child_ages": [],
                     "options": {"include_unpriced_itineraries": True, "include_mixed_booking_options": True},
                     "trusted_funnel_search_guid": "NVM", "state": {}}

        payload = {**TEMPLATE_CALL, **parsed_payload['culture'], **parsed_payload['searchParams'],
                   **{'trusted_funnel_search_guid': parsed_payload['funnelSearchGuid']}}
        payload["legs"] = [{"add_alternative_destinations": False,
                            "add_alternative_origins": False,
                            "date": payload["outboundDate"],
                            "destination": payload['destinationId'],
                            "origin": payload['originId'],
                            "return_date": payload["inboundDate"]}]
        payload = {key: payload[key] for key in GOOD_CALL.keys()}
        return payload

    def first_call(self):
        fy, fm, fd = self.from_date.split("-")
        ty, tm, td = self.to_date.split("-")
        parsed_to = ty[2:] + tm + td
        parsed_from = fy[2:] + fm + fd
        first_url = "https://www.skyscanner.co.il/transport/flights/{from_airport}/{to_airport}/{from_d}/{to_d}/?adults=1&children=0&adultsv2=1&childrenv2=&infants=0&cabinclass=economy&rtn=1&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false&ref=home".format(
            from_airport=self.from_airport,
            to_airport=self.to_airport,
            from_d=parsed_from,
            to_d=parsed_to
        )
        resp = requests.get(first_url)
        t = re.search("window\[\"__internal\"\]\s*=\s+({(.|\n)+?});", resp.text)
        j = re.sub("(\t|\n)", "", t.groups()[0])
        return json.loads(j)

    def second_call(self, payload):
        second_url = "https://www.skyscanner.co.il/g/conductor/v1/fps3/search/?geo_schema=skyscanner&carrier_schema=skyscanner&response_include=query%3Bdeeplink%3Bsegment%3Bstats%3Bfqs%3Bpqs"
        headers = {
            "Content-Type": "application/json",
            "user-agent": random_agent(),
            "x-skyscanner-channelid": "website",
            "x-skyscanner-devicedetection-ismobile": "false",
            "x-skyscanner-devicedetection-istablet": "false",
        }

        return requests.post(second_url, data=json.dumps(payload), headers=headers)

    def best_offer(self, resp):
        k = resp.json()
        if not k.get("itineraries"):
            return
        for i in sorted(filter(lambda x: x.get("score"), k.get("itineraries")), key=lambda x: x.get("score"),
                        reverse=True):
            for price in sorted(filter(lambda x: x.get("price").get("amount"), i.get("pricing_options")),
                                key=lambda x: x.get("price").get("amount")):
                return {**price, **{"score": i['score']}}


# (month, year, trip_days, to_airpot, from_airport="tlv"):
k = skyScraper.find_in_range(9, 2019, [10,14], 'hanv')
import json
with open("test.json", 'w') as f:
    json.dump(list(k), f)

