import requests
import re
import json


class skyScraper():
    def __init__(self, from_date, to_date, to_airport, from_airport="TLV"):
        self.from_date = from_date
        self.to_date = to_date
        self.to_airport = to_airport
        self.from_airport = from_airport

    def first_call(self):
        fy,fm,fd = self.from_date.split("-")
        ty,tm,td = self.to_date.split("-")
        parsed_to = ty[:2]+tm+td
        parsed_from = fy[:2]+fm+fd
        first_url = "https://www.skyscanner.co.il/transport/flights/{from_airport}/{to_airport}/{from_d}/{to_d}/?adults=1&children=0&adultsv2=1&childrenv2=&infants=0&cabinclass=economy&rtn=1&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false&ref=home".format(
            from_airport=self.from_airport,
            to_airport=self.to_airport,
            from_d=parsed_from,
            to_d=parsed_to
        )
        resp = requests.get(first_url)
        t = re.search("window\[\"__internal\"\]\s*=\s+({(.|\n)+?});",resp.text)
        j = re.sub("(\t|\n)", "", t.groups()[0])
        return json.loads(j)


print(skyScraper(from_date="2019-07-01", to_date="2019-07-20", to_airport="nyca").first_call())


