import streamlit as st
import requests
from itertools import product
import time
import os
import tempfile
from scidownl import scihub_download
from PyPDF2 import PdfMerger

# Use temporary directories instead of local directories
def get_temp_dirs():
    temp_base = tempfile.mkdtemp()
    papers_dir = os.path.join(temp_base, "papers")
    output_dir = os.path.join(temp_base, "output")
    os.makedirs(papers_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    return papers_dir, output_dir

def search_crossref(words, min_citations=10):
    url = "https://api.crossref.org/works"
    query = " ".join(words)
    params = {
        'query': query,
        'rows': 150,
        'select': 'title,DOI,is-referenced-by-count',
        'mailto': 'test@example.com'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()
        
        filtered_items = []
        for item in results['message']['items']:
            if 'title' not in item or not item['title']:
                continue
            title = item['title'][0].lower()
            citations = item.get('is-referenced-by-count', 0)
            if all(word.lower() in title for word in words) and citations >= min_citations:
                filtered_items.append((item, citations))
                
        return sorted(filtered_items, key=lambda x: x[1], reverse=True)
    
    except Exception as e:
        st.error(f"Error with query {query}: {str(e)}")
        return []

def download_and_merge_papers(source, progress_placeholder):
    papers_dir, output_dir = get_temp_dirs()
    downloaded_files = []
    total = len(source)
    
    progress_bar = progress_placeholder.progress(0)
    status_text = progress_placeholder.empty()
    
    for idx, (paper, paper_type, _) in enumerate(source):
        try:
            status_text.text(f'Downloading {paper} ({idx + 1}/{total})')
            out_file = os.path.join(papers_dir, f"{paper.replace('/', '_')}.pdf")
            scihub_download(paper, paper_type=paper_type, out=out_file)
            if os.path.exists(out_file):
                downloaded_files.append(out_file)
        except Exception as e:
            st.error(f"Failed to download {paper}: {e}")
        
        progress = (idx + 1) / total
        progress_bar.progress(progress)
        time.sleep(1)

    if downloaded_files:
        status_text.text('Merging PDFs...')
        try:
            merger = PdfMerger()
            for pdf in downloaded_files:
                if os.path.exists(pdf):
                    merger.append(pdf)
            output_path = os.path.join(output_dir, "merged.pdf")
            merger.write(output_path)
            merger.close()
            status_text.text('Download and merge completed!')
            return output_path
        except Exception as e:
            st.error(f"Error merging PDFs: {e}")
            return None
    return None

st.title('Search and download papers by list of keywords')

# [Rest of your UI code remains the same until the search button]

if st.button('Search and Download'):
    if all(word_lists):
        # Search phase
        st.subheader("Phase 1: Searching")
        search_progress = st.container()
        
        source = []
        seen_dois = set()
        word_combinations = list(product(*word_lists))
        
        progress_bar = search_progress.progress(0)
        status_text = search_progress.empty()
        
        for idx, combo in enumerate(word_combinations):
            status_text.text(f'Searching combination: {" + ".join(combo)}')
            results = search_crossref(combo, min_citations)
            
            for item, citations in results:
                if item["DOI"] not in seen_dois:
                    # Use temporary directory path
                    papers_dir, _ = get_temp_dirs()
                    source.append((item["DOI"], 'doi', papers_dir))
                    seen_dois.add(item["DOI"])
            
            progress = (idx + 1) / len(word_combinations)
            progress_bar.progress(progress)
            time.sleep(1)
        
        status_text.text('Search completed!')
        
        if source:
            st.text('Found DOIs:')
            for entry in source:
                st.code(f'("{entry[0]}", \'doi\', "[temp_dir]"),')
            
            # Download phase
            st.subheader("Phase 2: Downloading and Merging")
            download_progress = st.container()
            
            output_path = download_and_merge_papers(source, download_progress)
            
            if output_path and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    st.download_button(
                        'Download Merged PDF',
                        f,
                        'merged_papers.pdf',
                        'application/pdf'
                    )
            
            # Add download button for DOIs
            result_text = '\n'.join([f'"{entry[0]}",' for entry in source])
            st.download_button(
                'Download DOI List',
                result_text,
                'crossref_results.txt',
                'text/plain'
            )
        else:
            st.warning('No results found')
    else:
        st.error('Please enter keywords for all lists')
