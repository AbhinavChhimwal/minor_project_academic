import streamlit as st

from src.plagiarism_engine import PlagiarismEngine
from src.text_utils import extract_text_from_upload

st.set_page_config(page_title='AI Plagiarism Detector', layout='wide')
st.markdown(
    """
    <style>
      .hero-title { font-size: 34px; font-weight: 800; margin-top: 6px; }
      .pill { padding: 6px 12px; border-radius: 999px; display: inline-block; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); }
      .risk-low { color: #2dd4bf; }
      .risk-mid { color: #fbbf24; }
      .risk-high { color: #fb7185; }
    </style>
    <div class="hero-title">AI Assignment Plagiarism Checker</div>
    <div class="pill">Upload reference assignments, then check a submission instantly.</div>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_engine():
    return PlagiarismEngine()

import re
import html


def _token_set(text: str):
    # Token set for overlap highlighting.
    return {t.lower() for t in re.findall(r"[A-Za-z0-9']+", text)}


def highlight_overlap_html(query_text: str, candidate_text: str):
    query_tokens = _token_set(query_text)
    parts = re.split(r"(\s+)", candidate_text)
    out = []
    for part in parts:
        if part.isspace() or part == "":
            out.append(part)
            continue

        norm = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9']+$", "", part)
        if norm and norm.lower() in query_tokens:
            out.append(
                f'<span style="color:#fb7185; font-weight:700;">{html.escape(part)}</span>'
            )
        else:
            out.append(html.escape(part))
    return "".join(out)


with st.sidebar:
    st.header('Settings')
    threshold = st.slider('Flagging threshold (cosine similarity)', 0.30, 0.95, 0.75, 0.01)
    top_k = st.slider('Top matches to show', 3, 40, 12)
    st.caption('OCR is disabled. PDFs must contain selectable text.')

try:
    engine = get_engine()
except Exception as e:
    st.error('Failed to initialize plagiarism engine.')
    st.exception(e)
    st.stop()

tab1, tab2, tab3 = st.tabs(['Database Management', 'Plagiarism Check', 'Database Status'])

with tab1:
    st.subheader('1) Upload reference assignments (corpus)')
    st.caption('Upload multiple `.txt` files and/or PDFs that contain selectable text.')
    s1, s2 = st.columns(2)
    student_id = s1.text_input('Student ID (optional)', value='student_001')
    assignment_no = s2.number_input('Assignment number for these files', min_value=1, step=1, value=1)

    files = st.file_uploader('Upload assignments', type=['txt', 'pdf'], key='ref', accept_multiple_files=True)

    if st.button('Ingest uploaded assignments', type='primary'):
        if not files:
            st.warning('Please upload at least one file.')
        else:
            progress = st.progress(0, text='Ingesting...')
            added_docs = 0
            added_chunks = 0
            failed = []

            with st.spinner('Extracting text and indexing chunks...'):
                total = len(files)
                for i, file in enumerate(files):
                    progress.progress(int((i / total) * 100), text=f'Ingesting {file.name}...')

                    try:
                        text = extract_text_from_upload(file.name, file.getvalue())
                        if not text.strip():
                            failed.append(f'{file.name}: no selectable text found (OCR disabled)')
                            continue

                        result = engine.ingest_document(
                            file.name,
                            text,
                            student_id=student_id.strip() if student_id else None,
                            assignment_no=int(assignment_no) if assignment_no else None,
                        )
                        if result['chunks_added'] > 0:
                            added_docs += 1
                            added_chunks += result['chunks_added']
                        else:
                            failed.append(f'{file.name}: no readable text found')
                    except Exception as exc:
                        failed.append(f'{file.name}: {exc}')

            progress.progress(100, text='Done')
            st.success(f'Added {added_docs} document(s) with {added_chunks} total chunks.')
            if failed:
                st.warning('Some files were not ingested:')
                for item in failed:
                    st.write(f'- {item}')
            if added_chunks == 0:
                st.info('All files resulted in empty text. Make sure PDFs have selectable text.')

with tab2:
    st.subheader('2) Check a submission against your corpus')
    c1, c2 = st.columns(2)
    query_assignment_no = c1.number_input('Submission assignment number (N)', min_value=1, step=1, value=1)
    compare_assignment_no = c2.number_input(
        'Compare against assignment number (default N-1)',
        min_value=0,
        step=1,
        value=max(0, int(query_assignment_no) - 1),
    )
    st.caption('The submission (assignment N) will be compared only against the corpus of the selected compare assignment number.')

    query_file = st.file_uploader('Upload submission', type=['txt', 'pdf'], key='query')

    show_preview = st.toggle('Show extracted text preview', value=False)

    if st.button('Run plagiarism check', type='primary'):
        if not query_file:
            st.warning('Please upload a file first.')
        else:
            with st.spinner('Extracting text...'):
                text = extract_text_from_upload(query_file.name, query_file.getvalue())

            if not text.strip():
                st.error('No selectable text found in this PDF. OCR is disabled.')
                st.stop()

            if show_preview:
                with st.expander('Extracted text preview (truncated)', expanded=False):
                    st.text_area('Preview', text[:5000], height=250)

            with st.spinner('Searching for similar passages...'):
                report = engine.check_plagiarism(
                    text=text,
                    threshold=threshold,
                    top_k=top_k,
                    corpus_assignment_no=int(compare_assignment_no),
                )

            score = float(report['plagiarism_percent'])
            risk_class = "risk-low" if score < 40 else ("risk-mid" if score < 70 else "risk-high")
            score_int = int(max(0, min(100, score)))

            st.markdown(
                f"### Overall plagiarism risk: <span class='{risk_class}'>{score:.2f}%</span>",
                unsafe_allow_html=True,
            )
            st.progress(score_int, text=f'{score_int}% risk')

            c1, c2, c3 = st.columns(3)
            c1.metric('Total chunks', report['total_chunks'])
            c2.metric('Flagged chunks', report['matched_chunks'])
            c3.metric('Sources matched', len(report['document_breakdown']))

            st.divider()

            st.markdown('### Top matched passages')
            if not report['top_matches']:
                st.info('No matches found. Ingest reference assignments first.')
            else:
                for i, hit in enumerate(report['top_matches'], start=1):
                    sim = float(hit['similarity'])
                    sim_pct = int(max(0, min(100, sim * 100)))
                    flagged = bool(hit['is_flagged'])

                    with st.container(border=True):
                        st.write(f"**Match {i}**  |  Similarity: {sim:.2%}  |  {'FLAGGED' if flagged else 'not flagged'}")
                        st.progress(sim_pct, text=f"{sim_pct}%")
                        st.caption(f"Source document: {hit['source_document']}")

                        left, right = st.columns(2)
                        with left:
                            st.markdown('**Query chunk**')
                            st.write(hit['query_chunk'])
                        with right:
                            st.markdown('**Matched chunk**')
                            st.markdown(
                                highlight_overlap_html(hit['query_chunk'], hit['matched_chunk']),
                                unsafe_allow_html=True,
                            )

                        st.divider()

            st.markdown('### Document-level breakdown')
            if report['document_breakdown']:
                st.dataframe(report['document_breakdown'], use_container_width=True)
            else:
                st.write('No document had matches above your threshold.')

with tab3:
    st.subheader('Corpus overview')
    docs = engine.list_documents()
    if docs:
        assignment_values = sorted({d.get("assignment_no", None) for d in docs})
        assignment_options = ["All"] + [str(v) for v in assignment_values if v is not None]
        selected = st.selectbox('Filter by assignment number', assignment_options, index=0)

        if selected == "All":
            shown = docs
        else:
            selected_int = int(selected)
            shown = [d for d in docs if d.get("assignment_no", None) == selected_int]

        shown_display = [{k: v for k, v in d.items() if k != "db_id"} for d in shown]
        st.dataframe(shown_display, use_container_width=True)

        # Simple deletion UI
        delete_col1, delete_col2 = st.columns(2)
        with delete_col1:
            delete_options = [
                f"{d.get('id', '')}: {d.get('document_name', '')} | student={d.get('student_id', '')} | a{d.get('assignment_no', '')}"
                for d in shown
            ]
            if delete_options:
                selected_del = st.selectbox('Select document to delete', delete_options, index=0)
            else:
                selected_del = None
        with delete_col2:
            delete_assignment_label = None if selected == "All" else str(selected)
            if delete_assignment_label is None:
                st.caption('To delete by assignment no, select one in the filter above.')
                delete_all_btn = st.button('Delete all for this assignment number', disabled=True)
            else:
                delete_all_btn = st.button('Delete all for this assignment number', type='secondary')

        if selected_del and st.button('Delete selected document', type='secondary'):
            # Find the underlying document record from `shown`.
            # The string format starts with display id, so parse the prefix.
            try:
                display_id = int(selected_del.split(":")[0].strip())
            except Exception:
                display_id = None

            if display_id is None:
                st.error('Could not determine which document to delete.')
            else:
                match = next((d for d in shown if d.get("id") == display_id), None)
                if not match:
                    st.error('Selected document not found.')
                else:
                    engine.delete_document(match["db_id"])
                    st.success(f"Deleted: {match['document_name']} (student={match.get('student_id')}, a{match.get('assignment_no')})")
                    st.rerun()

        if delete_all_btn and selected != "All":
            engine.delete_documents_by_assignment_no(int(selected))
            st.success(f"Deleted all documents for assignment {selected}.")
            st.rerun()

        if st.button('Clear entire database'):
            engine.clear_database()
            st.success('Database cleared.')
            st.rerun()
    else:
        st.info('No documents in database yet.')
