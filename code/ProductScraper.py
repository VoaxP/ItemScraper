from flask import Flask, render_template, request
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from selenium.webdriver.common.keys import Keys
import re
import random
import os
import requests

app = Flask(__name__)

def scrape_hamleys(num_products):
    url = 'https://www.hamleys.com/offers/all-offers-at-hamleys?brand=Avatar~Harry%20Potter~Funko~Lego%C2%AE~Disney~Max~Ravensburger~WWE~Jurassic%20World~MGA~Nerf~Star%20Wars~Avengers~Barbie~Fortnite~Frozen~PJ%20Masks~Trolls~Timberkits~Poopsie~Pokemon~Marvel~MEGA~Lalaloopsy~L.O.L.%20Dolls~Hasbro~EUGY~Cocomelon~Bigjigs~Batman~Bakugan~BABY%20Born~Animal%20Crossing~Steiff~Peppa%20Pig~Paw%20Patrol~Brio~Oxford%20Diecast'

    # Set up the Selenium webdriver
    driver = webdriver.Chrome()
    driver.get(url)
    body = driver.find_element("tag name", "body")
    body.send_keys(Keys.PAGE_DOWN)
    time.sleep(2) 
    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, 'html.parser')
    product_elements = soup.find_all('a', class_='result')
    products = []

    if not product_elements:
        return products
    

    else:
        random.shuffle(product_elements)

        for product_elements in product_elements:
            # Extract product name
            product_name_elem = product_elements.find('h3', class_='result-title')
            product_name = product_name_elem.text.strip() if product_name_elem else "N/A"

            # Check if the product name is "N/A"
            if product_name == "N/A":
                continue

            # Extract product price
            price_elem = product_elements.select_one('div.price span.after_special') or product_elements.select_one('div.price span.promotion')
            product_price = price_elem.text.strip() if price_elem else "N/A"
            product_price_num = float(product_price.replace('£', '').replace(',', ''),)
            product_price_num = round(product_price_num , 2)

            # Extract image URL from link tag
            image_elem = product_elements.find('link', itemprop='image')
            img_url = image_elem['href'] if image_elem else None

            # If image URL not found in link tag, try img tag
            if not img_url:
                img_elem = product_elements.find('img', itemprop='image')
                img_url = img_elem['src'] if img_elem else "No Image Available"

            # Add product details to list
            products.append({
                'product_name': product_name,
                'product_price': product_price_num,
                'FBA_fee': None, 
                'productFBA_price': None, # Placeholders
                'amazon_price': None,  
                'image_url': img_url if img_url else "No Image Available"  
            })

            # Break the loop if enough products are found
            if len(products) == num_products:
                break

        return products
    
def get_lego_products(num_products):
    url = f'https://www.lego.com/en-gb/categories/sales-and-deals?page=2&offset={num_products}'

    # Set up the Selenium webdriver
    driver = webdriver.Chrome()  
    driver.get(url)
    driver.implicitly_wait(10)
    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, 'html.parser')
    product_elements = soup.find_all('article', class_='ProductLeaf_wrapper__H0TCb')
    products = []

    if not product_elements:
        return products

    else:
        random.shuffle(product_elements)

        for product_elements in product_elements:
            product_name = product_elements.find('span', class_='markup').text.strip()

            product_price_elem = product_elements.find('span', class_='ProductLeaf_discountedPrice__77YmG')
            product_price = product_price_elem.text.strip() 
            product_price_num = float(product_price.replace('£', '').replace(',', ''))
            product_price_num = round(product_price_num , 2)

            img_srcset = product_elements.find('source', type='image/webp')['srcset']
            img_urls = re.findall(r'https://.+?\.png', img_srcset)
            img_url = img_urls[0] if img_urls else None  # Using the first match if available
            
            products.append({
                'product_name': product_name,
                'product_price': product_price_num,
                'productFBA_price': None, # Placeholders
                'FBA_fee': None, 
                'amazon_price': None,  
                'image_url': img_url if img_url else "No Image Available"  
            })

            if len(products) == num_products:
                break
        return products

def is_sponsored(container):
    return container.find('span', class_='a-color-secondary') and 'Sponsored' in container.find('span', class_='a-color-secondary').text

def search_amazon(products):
    product_name = products['product_name']

    url = f'https://www.amazon.co.uk/s?k={product_name.replace(" ", "+")}'

    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')  # Set a user-agent to mimic a real browser
    options.add_argument('start-maximized')  # Maximize the window to ensure all elements are visible
    options.add_argument('disable-infobars')  # Disable infobars
    options.add_argument('--disable-extensions')  # Disable extensions
    options.add_argument('--disable-dev-shm-usage')  # Disable DevShmUsage
    options.add_argument('--disable-browser-side-navigation')  # Disable Browser side navigation
    options.add_argument('--disable-gpu')  # Disable GPU acceleration

    driver = webdriver.Chrome(options=options)
    delay = random.uniform(2, 5) 
    time.sleep(delay)

    try:
        driver.get(url)
        time.sleep(delay)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        product_elements = soup.find_all('div', class_='s-result-item')

        for elements in product_elements:
            if is_sponsored(elements):
                continue

            price_elem = elements.find('span', class_='a-price')
            if price_elem:
                price_whole_elem = price_elem.find('span', class_='a-price-whole')
                price_fraction_elem = price_elem.find('span', class_='a-price-fraction')
                if price_whole_elem and price_fraction_elem:
                    amazon_price = f"£{price_whole_elem.text.strip()}{price_fraction_elem.text.strip()}"
                    amazon_price_num = float(amazon_price.replace('£', '').replace(',', ''))
                    amazon_price_num = round(amazon_price_num, 2)
                    products['amazon_price'] = amazon_price_num

            # Extract star rating
            rating_elem = elements.find('span', {'aria-label': lambda x: x and 'out of 5 stars' in x})
            star_rating = rating_elem.find('span', class_='a-icon-alt').text.strip() if rating_elem else "Star Rating Not Found"
            products['star_rating'] = star_rating

            # Extract number of reviews
            review_elem = elements.find('span', class_='a-size-base')
            num_reviews = review_elem.text.strip() if review_elem else "Number of Reviews Not Found"
            products['num_reviews'] = num_reviews

            # Extract bought in past month
            bought_elem = elements.find('span', class_='a-color-secondary')
            bought_info = bought_elem.text.strip() if bought_elem else "No information available"
            if 'bought in past month' in bought_info:
                products['bought_past_month'] = bought_info if bought_info else "No previous sold data"

            # Extract RRP or Was price
            rrp_elem = elements.find('span', class_='a-size-base')
            rrp_info = rrp_elem.text.strip() if rrp_elem else ""
            if 'RRP:' in rrp_info or 'Was:' in rrp_info:
                price_container = elements.find('span', class_='a-price')
                if price_container:
                    rrp_whole_elem = price_container.find('span', class_='a-price-whole')
                    rrp_fraction_elem = price_container.find('span', class_='a-price-fraction')
                    if rrp_whole_elem and rrp_fraction_elem:
                        rrp_price = f"£{rrp_whole_elem.text.strip()}{rrp_fraction_elem.text.strip()}"
                        products['rrp_price'] = rrp_price if rrp_price else "No data found on discounted price"

            # Extract stock availability
            stock_elem = elements.find('span', class_='a-size-small')
            stock_availability = stock_elem.text.strip() if stock_elem else "Stock information not found"
            products['stock_availability'] = stock_availability

            image_elem = elements.find('img', class_='s-image')
            image_url = image_elem['src'] if image_elem else None

            # If both star rating and number of reviews are found, break out of the loop
            if star_rating != "Star Rating Not Found" and num_reviews != "Number of Reviews Not Found":
                break

        # Extract the image URL from the 'src' attribute
        if image_url:
            image_url = image_url.split('.jpg')[0] + '.jpg'
            products['amazon_image_url'] = image_url

    except Exception as e:
        print(f"Error occurred while scraping Amazon: {str(e)}")
    finally:
        driver.quit()

    return products

def calculate_productFBA_price(products):
    product_price = products['product_price']
    productFBA_price = round(product_price * 1.15, 2)
    products['productFBA_price'] = productFBA_price

def calculate_FBA_fee(products):
    product_price = products['product_price']
    FBA_fee = round(product_price * 0.15, 2)
    products['FBA_fee'] = FBA_fee
    
def calculate_roi(products):
    productFBA_price = products['productFBA_price']
    amazon_price = products['amazon_price']
    roi = round(((amazon_price - productFBA_price) / productFBA_price) * 100, 2)
    products['roi'] = roi
 
def calculate_profit_margin(products):
    productFBA_price = products['productFBA_price']
    amazon_price = products['amazon_price']
    
    # Check if amazon_price is not zero to avoid division by zero error
    if amazon_price != 0:
        profit_margin = round(((amazon_price - productFBA_price) / amazon_price) * 100, 2)
    else:
        profit_margin = 0  # Set profit margin to 0 if amazon_price is zero
    
    products['profit_margin'] = profit_margin

def product_analysis(products):
    if products['amazon_price'] is not None:
        amazon_price = products['amazon_price']
        productFBA_price = products['product_price']

        # Calculate FBA fee and FBA price
        calculate_FBA_fee(products)
        calculate_productFBA_price(products)

        # Calculate profit margin and ROI
        calculate_profit_margin(products)
        calculate_roi(products)

        # Calculate price difference and expected profit per item
        price_difference = (amazon_price - productFBA_price) / productFBA_price * 100
        price_difference_percentage = f"{round(price_difference, 2)}%"

        # Set the price difference message based on the price difference
        if productFBA_price > amazon_price:
            price_difference_message = "Amazon price is higher than productFBA price"
        elif price_difference >= 500:
            price_difference_message = "Extreme price difference detected"
        elif 400 <= price_difference < 500:
            price_difference_message = "High price difference detected"
        elif 300 <= price_difference < 400:
            price_difference_message = "Moderate price difference detected"
        else:
            price_difference_message = "Price difference within threshold"

        # Calculate expected profit per item
        expected_profit_per_item = amazon_price - productFBA_price

        # Assign calculated values to the product dictionary
        products['price_difference_message'] = (price_difference_message, price_difference_percentage)
        products['expected_profit_per_item'] = f"£{expected_profit_per_item:.2f}"

        # Add checks for empty or None values in fields
        if products['star_rating'] == "Star Rating Not Found":
            products['star_rating'] = "Star Rating Not Available"
        if products['num_reviews'] == "Number of Reviews Not Found":
            products['num_reviews'] = "Number of Reviews Not Available"
        if 'bought_past_month' not in products:
            products['bought_past_month'] = "No sales data available"
        if 'rrp_price' not in products:
            products['rrp_price'] = "No RRP or Was price available"

        return products
    else:
        # If Amazon price is None or empty, provide a message
        products['price_difference_message'] = "Amazon price not available"
        products['expected_profit_per_item'] = "Profit calculation not possible"
        return products
    
def send_discord_webhook(message):
    # Replace 'YOUR_DISCORD_WEBHOOK_URL' with your actual Discord webhook URL
    webhook_url = 'https://discord.com/api/webhooks/1214058141730340875/HPewMdfv37mptT6R4aW5UR4k6xm6bnPv2CV6OmgGLquALdTSvSBbQyRIVTf8sTd_OWn_'

    headers = {
        'Content-Type': 'application/json',
    }

    data = {
        'content': message,
    }

    response = requests.post(webhook_url, headers=headers, json=data)

    if response.status_code != 204:
        print(f"Failed to send message to Discord. Status code: {response.status_code}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        num_products = int(request.form['num_products'])
        if 'scrape_lego' in request.form:
            # If the Lego button is clicked, perform Lego scraping
            product_details = get_lego_products(num_products)
            updated_product_details = [search_amazon(product) for product in product_details]
            updated_product_details = [product_analysis(product) for product in updated_product_details]

            # Get filter values from the form
            review_count_filter = request.form.get('minReviews')
            max_price_filter = request.form.get('maxPrice')
            min_star_rating_filter = request.form.get('minStarRating')
            min_roi_filter = request.form.get('minROI')
            min_sold_filter = request.form.get('minSold')
            min_profit_filter = request.form.get('minProfit')

            # Convert to integers or floats if not empty, otherwise default to None
            review_count_filter = int(review_count_filter) if review_count_filter else None
            max_price_filter = float(max_price_filter) if max_price_filter else None
            min_star_rating_filter = float(min_star_rating_filter) if min_star_rating_filter else None
            min_roi_filter = float(min_roi_filter) if min_roi_filter else None
            min_sold_filter = int(min_sold_filter) if min_sold_filter else None
            min_profit_filter = float(min_profit_filter) if min_profit_filter else None

            # Apply filters
            filtered_products = []
            print(updated_product_details)
            for product in updated_product_details:
                # Function to convert "number of reviews" to integer
                def convert_num_reviews(num_reviews_str):
                    try:
                        return int(num_reviews_str.replace(',', ''))
                    except ValueError:
                        return 0

                # Function to convert "star rating" to float or 0
                def convert_star_rating(star_rating_str):
                    try:
                        return float(star_rating_str.split()[0])
                    except ValueError:
                        return 0

                # Function to convert "expected profit per item" to float or 0
                def convert_expected_profit(expected_profit_str):
                    try:
                        return float(expected_profit_str.split('£')[1])
                    except (ValueError, IndexError):
                        return 0

                # Function to convert "bought past month" to 0 if there's no sales data
                def convert_bought_past_month(bought_past_month_str):
                    if bought_past_month_str.lower() == 'no sales data available':
                        return 0
                    else:
                        try:
                            return int(bought_past_month_str.replace(',', ''))
                        except ValueError:
                            return 0

                product['num_reviews'] = convert_num_reviews(product['num_reviews'])
                product['star_rating'] = convert_star_rating(product['star_rating'])
                product['expected_profit_per_item'] = convert_expected_profit(product['expected_profit_per_item'])
                product['bought_past_month'] = convert_bought_past_month(product['bought_past_month'])

                # Apply filters only if they are not None
                if review_count_filter is not None and product.get('num_reviews', 0) < review_count_filter:
                    continue
                
                if max_price_filter is not None and product.get('product_price', 0) > max_price_filter:
                    continue
                
                if min_star_rating_filter is not None and product.get('star_rating', 0) < min_star_rating_filter:
                    continue
                
                if min_roi_filter is not None and product.get('roi', 0) < min_roi_filter:
                    continue
                
                if min_sold_filter is not None and product.get('bought_past_month', 0) < min_sold_filter:
                    continue
                
                if min_profit_filter is not None and product.get('expected_profit_per_item', 0) < min_profit_filter:
                    continue

                filtered_products.append(product)

                for product in filtered_products:
                    message = (
                        f"**------------------------------** \n"
                        f"**Name:** {product['product_name']}\n"
                        f"**Price:** {product['product_price']}\n"
                        f"**Amazon Price:** {product.get('amazon_price', 'N/A')}\n"
                        f"**FBA Price:** {product.get('productFBA_price', 'N/A')}\n"
                        f"**FBA Fee:** {product.get('FBA_fee', 'N/A')}\n"
                        f"**Star Rating:** {product.get('star_rating', 'N/A')}\n"
                        f"**Number of Reviews:** {product.get('num_reviews', 'N/A')}\n"
                        f"**ROI:** {product.get('roi', 'N/A')}\n"
                        f"**Profit Margin:** {product.get('profit_margin', 'N/A')}\n"
                        f"**Sold in past month:** {product.get('bought_past_month', 'N/A')}\n"
                        f"**RRP Price:** {product.get('rrp_price', 'N/A')}\n"
                        f"**Price difference:** {product.get('price_difference_message', 'N/A')}\n"
                        f"**Expected Profit per item:** {product.get('expected_profit_per_item', 'N/A')}\n"
                        f"**Image URL:** {product.get('image_url', 'N/A')}\n"
                        f"**Amazon Image URL:** {product.get('amazon_image_url', 'N/A')}\n"
                    )
                    send_discord_webhook("Scraped Lego Products:")
                    send_discord_webhook(message)

            return render_template('index.html', product_details=filtered_products)
    
        elif 'scrape_hamleys' in request.form:
            product_details = scrape_hamleys(num_products)
            updated_product_details = [search_amazon(product) for product in product_details]
            updated_product_details = [product_analysis(product) for product in updated_product_details]

            # Get filter values from the form
            review_count_filter = request.form.get('minReviews')
            max_price_filter = request.form.get('maxPrice')
            min_star_rating_filter = request.form.get('minStarRating')
            min_roi_filter = request.form.get('minROI')
            min_sold_filter = request.form.get('minSold')
            min_profit_filter = request.form.get('minProfit')

            # Convert to integers or floats if not empty, otherwise default to None
            review_count_filter = int(review_count_filter) if review_count_filter else None
            max_price_filter = float(max_price_filter) if max_price_filter else None
            min_star_rating_filter = float(min_star_rating_filter) if min_star_rating_filter else None
            min_roi_filter = float(min_roi_filter) if min_roi_filter else None
            min_sold_filter = int(min_sold_filter) if min_sold_filter else None
            min_profit_filter = float(min_profit_filter) if min_profit_filter else None

            # Apply filters
            filtered_products = []
            print(updated_product_details)
            for product in updated_product_details:
                # Function to convert "number of reviews" to integer
                def convert_num_reviews(num_reviews_str):
                    try:
                        return int(num_reviews_str.replace(',', ''))
                    except ValueError:
                        return 0

                # Function to convert "star rating" to float or 0
                def convert_star_rating(star_rating_str):
                    try:
                        return float(star_rating_str.split()[0])
                    except ValueError:
                        return 0

                # Function to convert "expected profit per item" to float or 0
                def convert_expected_profit(expected_profit_str):
                    try:
                        return float(expected_profit_str.split('£')[1])
                    except (ValueError, IndexError):
                        return 0

                # Function to convert "bought past month" to 0 if there's no sales data
                def convert_bought_past_month(bought_past_month_str):
                    if bought_past_month_str.lower() == 'no sales data available':
                        return 0
                    else:
                        try:
                            return int(bought_past_month_str.replace(',', ''))
                        except ValueError:
                            return 0

                product['num_reviews'] = convert_num_reviews(product['num_reviews'])
                product['star_rating'] = convert_star_rating(product['star_rating'])
                product['expected_profit_per_item'] = convert_expected_profit(product['expected_profit_per_item'])
                product['bought_past_month'] = convert_bought_past_month(product['bought_past_month'])

                # Apply filters only if they are not None
                if review_count_filter is not None and product.get('num_reviews', 0) < review_count_filter:
                    continue
                
                if max_price_filter is not None and product.get('product_price', 0) > max_price_filter:
                    continue
                
                if min_star_rating_filter is not None and product.get('star_rating', 0) < min_star_rating_filter:
                    continue
                
                if min_roi_filter is not None and product.get('roi', 0) < min_roi_filter:
                    continue
                
                if min_sold_filter is not None and product.get('bought_past_month', 0) < min_sold_filter:
                    continue
                
                if min_profit_filter is not None and product.get('expected_profit_per_item', 0) < min_profit_filter:
                    continue

                filtered_products.append(product)

                for product in filtered_products:
                    message = (
                        f"**------------------------------** \n"
                        f"**Name:** {product['product_name']}\n"
                        f"**Price:** {product['product_price']}\n"
                        f"**Amazon Price:** {product.get('amazon_price', 'N/A')}\n"
                        f"**FBA Price:** {product.get('productFBA_price', 'N/A')}\n"
                        f"**FBA Fee:** {product.get('FBA_fee', 'N/A')}\n"
                        f"**Star Rating:** {product.get('star_rating', 'N/A')}\n"
                        f"**Number of Reviews:** {product.get('num_reviews', 'N/A')}\n"
                        f"**ROI:** {product.get('roi', 'N/A')}\n"
                        f"**Profit Margin:** {product.get('profit_margin', 'N/A')}\n"
                        f"**Sold in past month:** {product.get('bought_past_month', 'N/A')}\n"
                        f"**RRP Price:** {product.get('rrp_price', 'N/A')}\n"
                        f"**Price difference:** {product.get('price_difference_message', 'N/A')}\n"
                        f"**Expected Profit per item:** {product.get('expected_profit_per_item', 'N/A')}\n"
                        f"**Image URL:** {product.get('image_url', 'N/A')}\n"
                        f"**Amazon Image URL:** {product.get('amazon_image_url', 'N/A')}\n"
                    )
                    send_discord_webhook("Scraped Hamleys Products:")
                    send_discord_webhook(message)

            return render_template('index.html', product_details=filtered_products)
    else:
        # If it's a GET request, render the template
        return render_template('index.html', product_details=[])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)