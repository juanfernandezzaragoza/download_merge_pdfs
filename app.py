import streamlit as st
import requests
from itertools import product
import time
import os
import tempfile
import sqlite3
from scidownl import scihub_download
from PyPDF2 import PdfMerger

# Use temporary directory for file operations in Streamlit Cloud
def get_temp_dir():
    temp_dir = tempfile.mkdtemp()
    # Create a SQLite database in the temp directory for scidownl
    db_path = os.path.join(temp_dir, 'scidownl.db')
    conn = sqlite3.connect(db_path)
    conn.close()
    # Set environment variable for scidownl to use our temporary database
    os.environ['SCIDOWNL_PATH'] = temp_dir
    return temp_dir

# Initialize directories using temp directories for Streamlit Cloud
TEMP_DIR = get_temp_dir()
PAPERS_DIR = os.path.join(TEMP_DIR, "papers")
OUTPUT_DIR = os.path.join(TEMP_DIR, "output")

# Monkey patch scidownl's database path
import scidownl.update_link
scidownl.update_link.PATH = os.path.join(TEMP_DIR, 'scidownl.db')

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
    os.makedirs(PAPERS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    downloaded_files = []
    total = len(source)
    
    progress_bar = progress_placeholder.progress(0)
    status_text = progress_placeholder.empty()
    
    for idx, (paper, paper_type, out) in enumerate(source):
        try:
            status_text.text(f'Downloading {paper} ({idx + 1}/{total})')
            out_file = os.path.join(out, f"{paper.replace('/', '_')}.pdf")
            scihub_download(paper, paper_type=paper_type, out=out_file)
            if os.path.exists(out_file):
                downloaded_files.append(out_file)
        except Exception as e:
            st.error(f"Failed to download {paper}: {e}")
        
        progress = (idx + 1) / total
        progress_bar.progress(progress)
        time.sleep(1)  # To avoid overwhelming the server

    if downloaded_files:
        status_text.text('Merging PDFs...')
        merger = PdfMerger()
        for pdf in downloaded_files:
            merger.append(pdf)
        output_path = os.path.join(OUTPUT_DIR, "merged.pdf")
        merger.write(output_path)
        merger.close()
        status_text.text('Download and merge completed!')
        return output_path
    return None

def main():
    st.title('Search and download papers by list of keywords')

    st.markdown("""
    ### 🔍 Research Assistant for NotebookLM

    I built this tool to **streamline my research workflow** with NotebookLM - a powerful AI tool for analyzing PDFs and generating insights through quick queries.

    **How it works:**
    * Enter **groups of keywords** (separated by spaces)
    * The app finds papers containing **at least one word from each group**
     
    *Example:*  
    Input 1: `laugh humor` 
    Input 2: `social evolution`  
    ✅ "Social Functions of Laughter in Evolution"  
    ✅ "Evolutionary Basis of Humor Behavior"  
    ❌ "Evolution of Social Behavior" (missing laugh/humor term)
    ❌ "Psychology of Humor" (missing social/evolution term)

    The app automatically searches Crossref for relevant titles and downloads PDFs through Sci-Hub, creating a ready-to-use collection for NotebookLM analysis.
    """)

    # Input for minimum citations
    min_citations = st.number_input('Minimum Citations', min_value=1, value=10)

    # Dynamic input for word lists
    num_lists = st.number_input('Number of keyword lists', min_value=1, max_value=5, value=2)
    word_lists = []

    for i in range(num_lists):
        words = st.text_input(f'Keywords list {i+1} (space-separated)', key=f'list_{i}')
        if words:
            word_lists.append(words.split())

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
                        source.append((item["DOI"], 'doi', PAPERS_DIR))
                        seen_dois.add(item["DOI"])
                
                progress = (idx + 1) / len(word_combinations)
                progress_bar.progress(progress)
                time.sleep(1)
            
            status_text.text('Search completed!')
            
            if source:
                st.text('Found DOIs:')
                for entry in source:
                    st.code(f'("{entry[0]}", \'doi\', PAPERS_DIR),')
                
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
                result_text = '\n'.join([f'("{entry[0]}", \'doi\', PAPERS_DIR),' for entry in source])
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

if __name__ == "__main__":
    main()
