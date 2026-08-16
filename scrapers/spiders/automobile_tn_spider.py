from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from urllib.parse import urljoin

import scrapy
from scrapy.http import Response

from scrapers.common.normalizers import (
    is_negotiable,
    normalize_fuel,
    normalize_gearbox,
    normalize_mileage,
    normalize_region,
    normalize_text,
)
from scrapers.common.schema import CarStatus, SellerType, Source


class AutomobileTNSpider(scrapy.Spider):
    name = "Automobile TN"
    source_name = Source.AUTOMOBILE_TN.value

    BASE_URL = "https://www.automobile.tn"
    START_URL = "https://www.automobile.tn/fr/occasion"
    MAX_PAGES = 100
    CURRENT_PAGE = 1

    async def start(self):
        yield scrapy.Request(
            url=self.START_URL,
            callback=self.parse_listing_pages,
            meta={"page": 1},
            errback=self.handle_error,
        )

    def parse_listing_pages(self, response: Response) -> Generator:
        page = response.meta.get("page", 1)
        self.logger.info(f"Parsing listing page {page} : {response.url}...")

        cards = response.css(".occasion-item-v2")

        if not cards:
            self.logger.warning(f"No car cards found on page {page} : {response.url}")
            return

        for card in cards:
            detail_url = card.css("a.occasion-link-overlay::attr(href)").get()

            if detail_url:
                full_url = urljoin(self.BASE_URL, detail_url)

                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_detail_page,
                    errback=self.handle_error,
                    meta={"source_page": page},
                )

        next_page_url = response.css(".page-item.next a::attr(href)").get()
        if next_page_url and page < self.MAX_PAGES:
            yield scrapy.Request(
                url=urljoin(self.BASE_URL, next_page_url),
                callback=self.parse_listing_pages,
                meta={"page": page + 1},
                errback=self.handle_error,
            )

    def parse_detail_page(self, response: Response) -> dict:
        self.logger.info(f"Parsing detail page: {response.url}...")

        listing_id = self.__extract_listing_id(response.url)

        title = normalize_text(response.css("h1.occasion-title::text").get())

        make = response.css(
            "li:contains('Marque') .spec-value::text, li:contains('Marque') .spec-value.text-end a::text"
        ).get()
        model = response.css(
            "li:contains('Modèle') .spec-value.text-end::text, li:contains('Modèle') .spec-value.text-end a::text"
        ).get()
        generation = response.css("li:contains('Génération') .spec-value::text").get()

        engine = response.css("li:contains('Moteur') .spec-value::text").get()
        cylinder_capacity = normalize_text(
            response.css("li:contains('Cylindrée') .spec-value::text").get()
        )
        if cylinder_capacity:
            try:
                cylinder_capacity = int(cylinder_capacity)
            except (ValueError, TypeError):
                cylinder_capacity = None

        year_raw = response.css(
            "li:contains('Mise en circulation') .spec-value::text"
        ).get()
        year = None
        if year_raw:
            try:
                year = int(year_raw.split(".")[-1])
            except (ValueError, IndexError, AttributeError):
                year = None

        mileage = response.css("li:contains('Kilométrage') .spec-value::text").get()
        mileage = normalize_mileage(mileage)

        fuel_type = normalize_fuel(
            response.css("li:contains('Énergie') .spec-value::text").get()
        )
        gearbox_type = normalize_gearbox(
            response.css("li:contains('Boite vitesse') .spec-value::text").get()
        )
        fiscal_power = normalize_text(
            response.css("li:contains('Puissance fiscale') .spec-value::text").get()
        )
        if fiscal_power:
            try:
                fiscal_power = int(fiscal_power)
            except (ValueError, TypeError):
                fiscal_power = None

        color = response.css(
            "li:contains('Couleur extérieure') .spec-value::text"
        ).get()
        doors = response.css("li:contains('Nombre de portes') .spec-value::text").get()
        if doors:
            try:
                doors = int(doors)
            except (ValueError, TypeError):
                doors = None

        places = response.css("li:contains('Nombre de places') .spec-value::text").get()
        if places:
            try:
                places = int(places)
            except (ValueError, TypeError):
                places = None

        general_status = response.css(
            "li:contains('État général') .spec-value span::text"
        ).get()
        # Map French status to enum
        status_mapping = {
            "très bon": CarStatus.GREAT,
            "bon": CarStatus.GOOD,
            "moyen": CarStatus.FAIR,
            "mauvais": CarStatus.POOR,
        }
        if general_status:
            general_status = status_mapping.get(
                general_status.lower().strip(), CarStatus.UNKNOWN
            )
        else:
            general_status = CarStatus.UNKNOWN

        owners = response.css(
            "li:contains('Anciens propriétaires') .spec-value::text"
        ).get()

        region = normalize_region(
            response.css("li:contains('Gouvernorat') .spec-value::text").get()
        )
        posted_at_raw = response.css(
            "li:contains('Date de l\\'annonce') .spec-value::text"
        ).get()
        posted_at = self.__parse_date(posted_at_raw)

        # Seller phone is scrapped as follows:
        # ["\n      ", "\n        xx xxx xxx", "\n      ", "\n        xx xxx xxx", "\n      ", "\n        xx xxx xxx"]
        # We take the second element, split by newline, and take the second part which is the phone number.
        # This is because the first element is just whitespace, and the phone numbers are in the odd indices.

        seller_name = response.css("div.box.pro div span::text").get()
        if seller_name:
            seller_type = SellerType.DEALER
        else:
            seller_type = SellerType.PRIVATE
        seller_address = response.css("div.box.pro p.address::text").get()
        seller_phone = response.css("a#phone.phone::text").getall()
        if seller_phone:
            seller_phone = seller_phone[1].split("\n")[1].strip()
        else:
            seller_phone = None

        # Image scrapping is done as follows:
        # The images are in a carousel with class "f-carousel__slide".
        # Since each image is lazy loaded, the URL is in the "data-src" attribute of the slide div.

        slides = response.css("div.f-carousel__slide")
        image_urls = []
        if not slides:
            self.logger.warning(
                f"No image slides found for listing {listing_id} : {response.url}"
            )
        else:
            for slide in slides:
                url = slide.attrib.get("data-src")
                if url:
                    image_urls.append(url)

        price_text = normalize_text(response.css("div.price::text").get())
        if price_text:
            price_text = price_text.replace(" ", "")
        price_float = float(price_text) if price_text else None
        negotiable = is_negotiable(
            " ".join(response.css("p.text ::text").getall()).strip()
        )

        return {
            "listing_id": listing_id,
            "source": self.source_name,
            "url": response.url,
            "title": title,
            "make": make,
            "model": model,
            "generation": generation,
            "engine": engine,
            "cylinder_capacity": cylinder_capacity,
            "year": year,
            "mileage_km": mileage,
            "fuel_type": fuel_type,
            "gearbox_type": gearbox_type,
            "color": color,
            "doors": doors,
            "fiscal_power": fiscal_power,
            "places": places,
            "usage_status": owners,
            "global_status": general_status,
            "price_tnd": price_float,
            "price_raw": price_text,
            "negotiable": negotiable,
            "region": region,
            "seller_type": seller_type,
            "seller_name": seller_name,
            "seller_phone": seller_phone,
            "seller_address": seller_address,
            "image_urls": image_urls,
            "posted_at": posted_at,
        }

    def __extract_listing_id(self, url: str) -> str | None:
        parts = url.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            return parts[-1]
        return None

    def __parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None

        date_str = date_str.strip()

        try:
            return datetime.strptime(date_str, "%d.%m.%Y").replace(
                tzinfo=datetime.timezone.utc
            )
        except ValueError:
            self.logger.warning(f"Failed to parse date '{date_str}'")
            return None

    def handle_error(self, failure):
        self.logger.error(
            f"[{self.name}] Request failed: {failure.request.url} — {failure.value!r}"
        )
