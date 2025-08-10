from serpapi import GoogleSearch
import csv
import time
import requests
import json

SERPAPI_KEY = "17b976ffdc13092dfb3ce674c7c387cf6efa363a4984ce352133a1173459b337"

dois_to_search = [
"10.1002/ajhb.23516",
"10.1007/978-3-030-23773-8",
]

output_csv_file = 'output.csv'
all_cited_by_articles = []

# Get article title from DOI using Crossref API
def get_title_from_doi(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data['message']['title'][0]
    except Exception as e:
        print(f"Error fetching title for DOI {doi}: {e}")
    return None

def search_by_title(title, api_key):
    params = {
        "engine": "google_scholar",
        "q": f'"{title}"',  # Use exact phrase search
        "api_key": api_key,
        "hl": "en"
    }
    
    search = GoogleSearch(params)
    try:
        results = search.get_dict()
        return results
    except Exception as e:
        print(f"Error in title search: {e}")
        return {}

def get_citing_articles(cites_id, api_key, max_results=None):
    citing_articles = []
    start = 0
    page_size = 20
    
    while True:
        print(f"  Fetching citing articles page {start//page_size + 1} (results {start}-{start+page_size-1})")
        
        params = {
            "engine": "google_scholar",
            "cites": cites_id,
            "api_key": api_key,
            "num": page_size,
            "start": start,
            "hl": "en",
            "as_sdt": "0,5"
        }
        
        search = GoogleSearch(params)
        try:
            results = search.get_dict()
            
            # Debug: print the keys in the response
            print(f"    Response keys: {list(results.keys())}")
            
            organic_results = results.get("organic_results", [])
            
            if not organic_results:
                if start == 0:
                    print(f"    No citing articles found on first page")
                    # Debug: print the full response for troubleshooting
                    print(f"    Full response: {json.dumps(results, indent=2)}")
                break
            
            print(f"    Found {len(organic_results)} articles on this page")
            
            for article in organic_results:
                citing_articles.append(article)
            
            # Check if we've reached the end or hit our limit
            if len(organic_results) < page_size:
                print(f"    Reached end of results (got {len(organic_results)} < {page_size})")
                break
                
            if max_results and len(citing_articles) >= max_results:
                print(f"    Reached maximum results limit ({max_results})")
                citing_articles = citing_articles[:max_results]
                break
            
            start += page_size
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"    Error fetching citing articles: {e}")
            break
    
    return citing_articles

def extract_article_info(article, original_doi):
    title = article.get("title", "N/A")
    
    publication_info = article.get("publication_info", {})
    authors = publication_info.get("authors", [])
    authors_str = ", ".join([author.get("name", "") for author in authors]) if authors else "N/A"
    
    year = "N/A"
    summary = publication_info.get("summary", "")
    if summary:
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', summary)
        if year_match:
            year = year_match.group()
            
    venue = summary if summary else "N/A"
    
    link = article.get("link", "N/A")
    
    return {
        "original_doi": original_doi,
        "citing_title": title,
        "citing_authors": authors_str,
        "citing_year": year,
        "citing_venue": venue,
        "citing_link": link
    }

# main loop
for doi in dois_to_search:
    print(f"\n{'='*60}")
    print(f"Processing DOI: {doi}")
    print(f"{'='*60}")
    
    # Get title from DOI
    title = get_title_from_doi(doi)
    if not title:
        print(f"❌ Could not find title for DOI: {doi}")
        continue
    
    print(f" Found title: {title}")
    
    # Search for the article by title
    search_results = search_by_title(title, SERPAPI_KEY)
    
    organic_results = search_results.get("organic_results", [])
    if not organic_results:
        print(f"No search results found for title")
        continue
    
    # first result's citation information
    first_result = organic_results[0]
    print(f" Found article: {first_result.get('title', 'N/A')}")
    
    cited_by_info = first_result.get("inline_links", {}).get("cited_by", {})
    if not cited_by_info:
        cited_by_info = first_result.get("cited_by", {})
    
    if not cited_by_info:
        print(f"No citation information found")
        continue
    
    total_citations = cited_by_info.get("total", 0)
    cites_id = cited_by_info.get("cites_id")
    
    if not cites_id:
        print(f"No cites_id found")
        continue
    
    print(f"Found {total_citations} total citations (cites_id: {cites_id})")
    
    citing_articles = get_citing_articles(cites_id, SERPAPI_KEY)
    
    if citing_articles:
        print(f"Successfully retrieved {len(citing_articles)} citing articles")
        
        for article in citing_articles:
            article_info = extract_article_info(article, doi)
            all_cited_by_articles.append(article_info)
    else:
        print(f"No citing articles retrieved")
    
    time.sleep(3)

# write to csv
if all_cited_by_articles:
    fieldnames = ['original_doi', 'citing_title', 'citing_authors', 'citing_year', 'citing_venue', 'citing_link']
    
    with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_cited_by_articles)
    
    print(f"\n SUCCESS!")
    print(f" {len(all_cited_by_articles)} total citing articles written to {output_csv_file}")
    
    # Print summary by DOI
    doi_counts = {}
    for article in all_cited_by_articles:
        doi = article['original_doi']
        doi_counts[doi] = doi_counts.get(doi, 0) + 1
    
    print("\nSummary by DOI:")
    for doi, count in doi_counts.items():
        print(f"   {doi}: {count} citing articles")
        
else:
    print("\n No citing articles found for any DOIs.")

