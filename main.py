from scraper import run_scrape
start = '2022-01-01' # date of first document
end = '2022-12-31' # date of last document
document_types = ['PRESS_RELEASE',"SPEECH"] # which documents to run for
# document_types = [1, 2]
output = run_scrape(start, end, document_types) # returns all documents for 2022