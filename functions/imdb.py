import time
import json
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_movies_by_year(minimun_rate, movie_year_start, movie_rating_count, csv_filename, batch_size, max_reviews_config):
    """Scrapes all movies from IMDb search results for a given year and writes to CSV every `batch_size` movies"""

    search_url = f'https://www.imdb.com/search/title/?title_type=feature&release_date={movie_year_start}-01-01,{movie_year_start}-12-31&user_rating={minimun_rate},10&num_votes={movie_rating_count},&sort=alpha,asc'
    
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(search_url)

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ipc-metadata-list-summary-item')))

    movies_data = []
    movie_count = 0 

    def load_all_movies(driver):
        while True:
            try:
                load_more_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "ipc-see-more__button")]'))
                )
                driver.execute_script('arguments[0].scrollIntoView();', load_more_button)
                driver.execute_script('arguments[0].click();', load_more_button)
                time.sleep(2)
                print('[Load More] Clicked button')
            except:
                print('[Load More] No more button')
                break
    
    load_all_movies(driver)

    while True:
        try:
            movie_elements = driver.find_elements(By.CLASS_NAME, 'ipc-metadata-list-summary-item')

            if not movie_elements:
                print('No movies found for year {movie_year_start}')
                driver.quit()
                return
            
            for movie in movie_elements:
                try:
                    # Get Movie ID
                    movie_link = movie.find_element(By.CLASS_NAME, 'ipc-title-link-wrapper').get_attribute('href')
                    movie_id = movie_link.split('/')[4]

                    # Get Movie Name (Remove Leading Number)
                    title_element = movie.find_element(By.CLASS_NAME, 'ipc-title__text')
                    raw_title = title_element.text
                    title = re.sub(r'^\d+\.\s*', '', raw_title)

                    # Get metadata (Year, Runtime)
                    metadata_elements = movie.find_elements(By.CSS_SELECTOR, 'div.dli-title-metadata span.dli-title-metadata-item')
                    year = metadata_elements[0].text if len(metadata_elements) > 0 else 'Not Found'
                    runtime = metadata_elements[1].text if len(metadata_elements) > 1 else 'Not Found'

                    # Get IMDb Rating
                    try:
                        rating_element = movie.find_element(By.CLASS_NAME, 'ipc-rating-star--rating')
                        imdb_rating = rating_element.text.strip()
                    except:
                        imdb_rating = 'Not Found'

                    # Get IMDb Vote Count
                    try:
                        vote_count_element = movie.find_element(By.CLASS_NAME, 'ipc-rating-star--voteCount')
                        imdb_vote_count = vote_count_element.text.replace('-', '').strip()
                    except:
                        imdb_vote_count = 'Not Found'

                    # Get Movie Details (Genres, Director)
                    movie_info = get_movie_page_details(movie_id)

                    # Get Movie Reviews (limit to 10)
                    movie_reviews = get_movie_reviews(movie_id, max_reviews_config)

                    # Store all data
                    movies_data.append({'Movie ID': movie_id,
                                        'Movie Year': year,
                                        'Movie Genres': ", ".join(movie_info['Movie Genres']),
                                        'Movie Director': movie_info['Movie Director'],
                                        'Movie Name': title,
                                        'Movie Runtime': runtime,
                                        'Movie Storyline': movie_info['Movie Storyline'],
                                        'Movie Country': movie_info['Movie Country'],
                                        'Movie Language': movie_info['Movie Language'],
                                        'IMDb Rating': imdb_rating,
                                        'IMDb Vote Count': imdb_vote_count,
                                        'Rating Detail': json.dumps(movie_reviews, ensure_ascii=False)
                                       })

                    movie_count += 1

                    # Write file every movie_count == batch_size
                    if movie_count % batch_size == 0:
                        df = pd.DataFrame(movies_data)

                        # Append to CSV (Not create header if that isn't first movie)
                        df.to_csv(csv_filename, mode='a', index=False, header=(movie_count == batch_size))

                        print(f"[SAVED] {movie_count} movies to {csv_filename}")
                        movies_data.clear()

                except Exception as e:
                    print(f'Error retrieving movie details: {e}')
            
        except Exception as e:
            print(f'Error loading movie list: {e}')
            break

    # Save remaining data that hasn't been written yet
    if movies_data:
        df = pd.DataFrame(movies_data)
        df.to_csv(csv_filename, mode='a', index=False, header=(movie_count < batch_size))
        print(f"[FINAL SAVE]: {movie_count} movies to {csv_filename}")

    driver.quit()

def get_movie_page_details(movie_id):
    """Extracts genres, director, storyline, country of origin, and language from a movie's IMDb page."""
    
    movie_url = f'https://www.imdb.com/title/{movie_id}/'
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    driver.get(movie_url)

    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'ipc-chip__text')))

    try:
        # Get Genres
        try:
            genre_elements = driver.find_elements(By.XPATH, '//a[contains(@class, "ipc-chip")]/span[contains(@class, "ipc-chip__text")]')
            genres = [genre.text.strip() for genre in genre_elements] if genre_elements else ['Not Found']
        except:
            genres = ['Not Found']

        # Get Director
        try:
            director_element = driver.find_element(By.XPATH, '//*[@id="__next"]/main/div/section[1]/section/div[3]/section/section/div[3]/div[2]/div[2]/div[2]/div/ul/li[1]/div/ul/li/a')
            director = director_element.text.strip()
        except:
            director = 'Not Found'

        # Get Storyline
        try:
            storyline_element = driver.find_element(By.CLASS_NAME, 'ipc-html-content-inner-div')
            storyline = storyline_element.text.strip()
        except:
            storyline = 'Not Found'

        # Get Country of Origin
        try:
            country_element = driver.find_element(By.XPATH, '//li[@data-testid="title-details-origin"]//a')
            country = country_element.text.strip()
        except:
            country = 'Not Found'

        # Get Movie Language
        try:
            language_element = driver.find_element(By.XPATH, '//li[@data-testid="title-details-languages"]//a')
            language = language_element.text.strip()
        except:
            language = 'Not Found'

    except Exception as e:
        print(f'Error retrieving movie page details: {e}')
        driver.quit()
        return None

    driver.quit()
    return {
        'Movie Genres': genres,
        'Movie Director': director,
        'Movie Storyline': storyline,
        'Movie Country': country,
        'Movie Language': language
    }

def get_movie_reviews(movie_id, max_reviews_config):
    """Extracts up to 10 user reviews for a given movie from IMDb."""
    
    reviews_url = f'https://www.imdb.com/title/{movie_id}/reviews/?sort=num_votes%2Cdesc&spoilers=EXCLUDE'
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(reviews_url)

    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'sc-7d2e5b85-1')))

    reviews_data = []

    try:
        # Get all review elements
        review_elements = driver.find_elements(By.CLASS_NAME, 'sc-7d2e5b85-1.cvfQlw.user-review-item')

        # Limit to max 10 reviews
        max_reviews = min(len(review_elements), 10)

        for review in review_elements[:max_reviews]:
            try:
                title = review.find_element(By.CLASS_NAME, 'ipc-title__text').text.strip()
            except:
                title = 'Not Found'

            try:
                rating = review.find_element(By.CLASS_NAME, 'ipc-rating-star--rating').text.strip()
            except:
                rating = 'Not Found'

            try:
                content = review.find_element(By.CLASS_NAME, 'ipc-html-content-inner-div').text.strip()
            except:
                content = 'Not Found'

            try:
                upvote = review.find_element(By.CLASS_NAME, 'ipc-voting__label__count--up').text.strip()
            except:
                upvote = '0'

            try:
                downvote = review.find_element(By.CLASS_NAME, 'ipc-voting__label__count--down').text.strip()
            except:
                downvote = '0'

            try:
                reviewer = review.find_element(By.CLASS_NAME, 'ipc-link.ipc-link--base').text.strip()
            except:
                reviewer = 'Anonymous'

            reviews_data.append({
                'Title': title,
                'Rating': rating,
                'Review Content': content,
                'Upvotes': upvote,
                'Downvotes': downvote,
                'Reviewer': reviewer
            })

    except Exception as e:
        print(f'Error retrieving reviews: {e}')

    driver.quit()
    return reviews_data