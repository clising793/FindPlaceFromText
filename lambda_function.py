import json
import requests

def get_place_details(search_string, location_query, api_key):
    base_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    place_details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"

    # Convert location query to latitude and longitude
    geocode_params = {
        'address': location_query,
        'key': api_key
    }
    geocode_response = requests.get(geocode_url, params=geocode_params)
    if geocode_response.status_code != 200:
        return None

    geocode_result = geocode_response.json()
    if 'results' not in geocode_result or not geocode_result['results']:
        return None

    location = geocode_result['results'][0]['geometry']['location']
    location_bias = f'point:{location["lat"]},{location["lng"]}'

    params = {
        'input': search_string,
        'inputtype': 'textquery',
        'fields': 'place_id',
        'locationbias': location_bias,
        'key': api_key
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return None

    result = response.json()
    if 'candidates' not in result or not result['candidates']:
        return None

    places_info = []
    for candidate in result['candidates']:
        place_id = candidate['place_id']

        details_params = {
            'place_id': place_id,
            'fields': 'name,rating,user_ratings_total,formatted_address,website,formatted_phone_number,types,url',
            'key': api_key
        }

        details_response = requests.get(place_details_url, params=details_params)
        if details_response.status_code != 200:
            continue

        details_result = details_response.json()
        if 'result' not in details_result:
            continue

        place = details_result['result']
        address_components = place.get('formatted_address', '').split(', ')
        street = address_components[0] if len(address_components) > 0 else None
        city = address_components[1] if len(address_components) > 1 else None
        state = address_components[2] if len(address_components) > 2 else None
        country_code = address_components[3] if len(address_components) > 3 else None

        places_info.append({
            'title': place.get('name'),
            'totalScore': place.get('rating'),
            'reviewsCount': place.get('user_ratings_total'),
            'street': street,
            'city': city,
            'state': state,
            'countryCode': country_code,
            'website': place.get('website'),
            'phone': place.get('formatted_phone_number'),
            'categoryName': place.get('types')[0] if place.get('types') else None,
            'url': place.get('url')
        })

    return places_info

def get_places_info(search_strings_array, location_query, api_key, webhook_url):
    places_info = []
    for search_string in search_strings_array:
        place_info_list = get_place_details(search_string, location_query, api_key)
        for place_info in place_info_list:
            places_info.append(place_info)
            send_to_webhook(place_info, webhook_url)
    return places_info

def send_to_webhook(data, webhook_url):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
    if response.status_code == 200:
        print("Data successfully sent to webhook.")
    else:
        print(f"Failed to send data to webhook. Status code: {response.status_code}")

def lambda_handler(event, context):
    body = event.get('body')
    if not body:
        return {
            'statusCode': 400,
            'body': json.dumps('Request body is missing.')
        }
    
    try:
        request_data = json.loads(body)
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid JSON format.')
        }

    search_strings_array = request_data.get('search_strings_array')
    location_query = request_data.get('location_query')
    webhook_url = request_data.get('webhook_url')
    api_key = 'YOUR_API_KEY'  # Replace with your actual Google API key

    if not search_strings_array or not webhook_url or not location_query:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing search_strings_array, location_query, or webhook_url in request body.')
        }

    places_info = get_places_info(search_strings_array, location_query, api_key, webhook_url)
    return {
        'statusCode': 200,
        'body': json.dumps(places_info)
    }

# Example event for testing locally
if __name__ == "__main__":
    example_event = {
        'body': json.dumps({
            'search_strings_array': ["Popeye's Grill"],
            'location_query': "New York, USA",
            'webhook_url': 'https://swr5cg4vp0.execute-api.eu-west-1.amazonaws.com/prod/process'
        })
    }
    context = {}  # Placeholder context object
    response = lambda_handler(example_event, context)
    print(response)
