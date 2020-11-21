import csv
from json.decoder import JSONDecodeError
import random
import re
from urllib.parse import unquote

import requests


class ShopMediaScrapper:
    STORE_FILE_NAME = 'stores.csv'
    
    STORE_FILE_URL_COLUMN_NAME = 'url'
    SCRAPING_ENDPOINTS = (
        '/',
        '/pages/about',
        '/pages/about-us',
        '/contact',
        '/contact-us'
    )

    PRODUCT_LIST_ENDPOINT = '/collections/all'
    
    SCRAPING_REGEX_TWITTER = re.compile(r"https?:\/\/(?:www\.)?twitter\.com\/[a-zA-Z0-9-._]*")
    SCRAPING_REGEX_FACEBOOK = re.compile(r"https?:\/\/(?:www\.)?facebook\.com\/[a-zA-Z0-9-._]*")
    SCRAPING_REGEX_EMAIL = re.compile(r"[a-z0-9-.]+@[a-z.]+")
    SCRAPING_REGEX_PRODUCT = re.compile(r"/collections/all/products/[^\"]+")

    STORE_INFO_REGEXES = {
        'twitter': SCRAPING_REGEX_TWITTER,
        'facebook': SCRAPING_REGEX_FACEBOOK,
        'email': SCRAPING_REGEX_EMAIL
    }

    NUMBER_OF_PRODUCTS = 5

    OUTPUT_FILE_NAME = 'output.csv'
    OUTPUT_COLUMNS = [
        'shop_url', 'twitter', 'facebook', 'email', 'product_0_title', 'product_0_img_src',
        'product_1_title', 'product_1_img_src', 'product_2_title', 'product_2_img_src', 'product_3_title',
        'product_3_img_src', 'product_4_title', 'product_4_img_src'
    ]

    def scrape_shop_product_info(self, host):
        uri = f'http://{host}{self.PRODUCT_LIST_ENDPOINT}'
        response = requests.get(uri)  # Redirections will be followed by default
        
        output = {}

        if response.status_code != 200:
            print(f'[+] ERROR: Endpoint {uri} returns status code {response.status_code}')
            return output
        
        # If shop would have the same product displayed twice, then ignore it and
        product_links = [
            *{*(self.SCRAPING_REGEX_PRODUCT.findall(response.text))}
        ][:self.NUMBER_OF_PRODUCTS]
        
        shop_is_productless = not product_links

        if shop_is_productless:
            print(f'[+] ERROR: {host} has no products!')
        
        for i, product_link in enumerate(product_links):
            title, image = None, None

            if not shop_is_productless:
                product_url = f'http://{host}{product_link}.json'
                response = requests.get(product_url) # Redirections will be followed by default
                if response.status_code != 200:
                    print(f'ERROR: Product {product_url} has no JSON data available')
                else:
                    try:
                        title = response.json()['product']['title']
                        image = response.json()['product']['image']['src']
                    except (JSONDecodeError, TypeError, KeyError):
                        print(f'[+] {product_url} is not a valid JSON')

            output[f'product_{i}_title'] = title 
            output[f'product_{i}_img_src'] = image

        return output

    def _select_accurate_socials(self, socials_list, host):
        """
        Shop page could scrape incorrect Social media links. Now we have
        to pick up the most probable, valid Social media links. If scraped
        links will have some similarity with hostname, they will score higher.

        The link with the highest amount of score will be considered the most
        accurate and returned.
        """

        scoring_words = host[:host.find('.')].split('-')
        score_dict = {}

        # Removes duplicates. So we dont iterate the same thing over and over.
        unique_socials = set(socials_list) 

        for social_media_link in socials_list:
            score = 0
            sanitized_social_media_link = unquote(social_media_link).strip().lower()
            for scoring_word in scoring_words:
                if sanitized_social_media_link.find(scoring_word) > -1:
                    score += 1
                
            if score not in score_dict:
                score_dict[score] = []

            score_dict[score].append(social_media_link)
            
        if not score_dict:
            return None
        else:
            # These scored the most. If there are more than one
            # winners, select one randomly and return it.
            winners = score_dict[max(score_dict.keys())]
            return winners[random.randint(0, len(winners) - 1)]

    def scrape_shop_contact_info(self, host):
        output = {key: [] for key in self.STORE_INFO_REGEXES.keys()}
        
        for endpoint in self.SCRAPING_ENDPOINTS:
            uri = f'http://{host}{endpoint}'
            response = requests.get(uri) # Redirections will be followed by default

            if response.status_code != 200:
                print(f'[+] NOTICE: Endpoint {uri} returns status code {response.status_code}')
                continue
            
            for key, rgx in self.STORE_INFO_REGEXES.items():
                found = rgx.findall(response.text)
                if found is not None:
                    output[key].extend(found)
        
        for key, scraped_socials in output.items():
            output[key] = self._select_accurate_socials(scraped_socials, host)

        return output
    
    def start_scraping(self):
        print('[+] Scraping started...')

        with open(self.STORE_FILE_NAME) as input_file, open(self.OUTPUT_FILE_NAME, 'w') as output_file:
            # reader works as iterator. Efficient.
            input_reader = csv.reader(input_file, delimiter='\t')
            output_writer = csv.DictWriter(output_file, fieldnames=self.OUTPUT_COLUMNS)
            output_writer.writeheader()

            try:
                # First CSV line is a header line 
                url_column_index = input_reader.__next__().index(self.STORE_FILE_URL_COLUMN_NAME)
            except ValueError:
                print(
                    f'[+] Column {self.STORE_FILE_URL_COLUMN_NAME} is '
                    f'not found in {self.STORE_FILE_NAME}. Exiting...'
                )
                return

            for line in input_reader:
                shop_host = line[url_column_index]

                single_shop_output = {'shop_url': shop_host}
                single_shop_output.update(
                    self.scrape_shop_contact_info(shop_host)
                )
                single_shop_output.update(
                    self.scrape_shop_product_info(shop_host)
                )

                # Wierd signs are because of green text output!
                print(f"\033[92m[+] Shop {shop_host} has been exported succesfully.\033[0m")
                output_writer.writerow(single_shop_output)


if __name__ == '__main__':
    scraper = ShopMediaScrapper()
    scraper.start_scraping()
