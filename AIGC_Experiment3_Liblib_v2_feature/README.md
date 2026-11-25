# AIGC Experiment 3 — v2 Feature Complexity Revision

This version is based directly on the previous v2 interface. Navigation, condition selection, LiblibAI API flow, layout, A1/A2/A3 structure, history, logging, and generation workflow are retained.

## Experimental controls
- A1/A2/A3 = design complexity
- B1 = low feature complexity: restrained, uniform visual language
- B2 = high feature complexity: additional visual hierarchy, badges, labels, metadata, gradients, and visual grouping without adding experimental functions

## Removed non-functional prototype controls
- Local inpainting
- Comparison view

These were removed because they were only prototype buttons and did not perform the corresponding functions.

## Run
```bat
cd /d C:\Users\X\Desktop\AIGC_Experiment3_Liblib_v2_feature
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
