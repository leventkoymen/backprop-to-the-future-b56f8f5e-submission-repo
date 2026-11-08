# Roadmap: tracking immunotherapy resistance (research use)

Research use by labs. Not built for the hackathon. No patient data used.

Among 157 patients whose advanced NSCLC progressed on first-line immunotherapy, median progression-free survival was 7.6 months (He et al., 2025). Some resistance is genetic: tumours can stop displaying antigen to T cells (B2M, HLA) or stop responding to interferon-gamma (JAK1/2). These changes can differ between tumours in the same patient and may exist before treatment starts (Sharma et al., 2017). In NSCLC tissue from 82 patients biopsied before and after immunotherapy, 27.8% gained loss-of-function mutations in STK11, B2M, APC, MTOR, KEAP1 or JAK1/2 (Ricciuti et al., 2024).

LungPair's next stage would take blood sequencing (ctDNA) results at baseline and then monthly, flag when one of these changes appears, and re-rank drug pairs for the next lab batch. Blood suits repeat testing: it is easier to sample serially and pools DNA from several metastatic sites, while a biopsy covers one site at one time (Pascual et al., 2022).

Limits:

- About seven in ten resistant tumours in the Ricciuti study showed no such mutation.
- We found no study that tracks these changes in blood, and blood assays detect copy-number changes and fusions poorly (Pascual et al., 2022). B2M can be lost by deletion (Sharma et al., 2017).
- NCI-ALMANAC has no immune cells, so LungPair can rank how well a pair kills tumour cells carrying these mutations, not whether it restores the immune response.
- This stage needs consented serial ctDNA and outcome data from patients on immunotherapy. The hackathon build uses no patient data.

## References

- He Q, Guo X-b, Chen Y-r, et al. The progression patterns and subsequent treatments of first-line immunotherapy in advanced non-small cell lung cancer: a retrospective cohort study. *Thorac Cancer*. 2025;16(20):e70173. doi:10.1111/1759-7714.70173
- Ricciuti B, Lamberti G, Puchala SR, et al. Genomic and immunophenotypic landscape of acquired resistance to PD-(L)1 blockade in non-small-cell lung cancer. *J Clin Oncol*. 2024;42(11):1311-1321. doi:10.1200/JCO.23.00580
- Pascual J, Attard G, Bidard F-C, et al. ESMO recommendations on the use of circulating tumour DNA assays for patients with cancer: a report from the ESMO Precision Medicine Working Group. *Ann Oncol*. 2022;33(8). doi:10.1016/j.annonc.2022.05.520
- Sharma P, Hu-Lieskovan S, Wargo JA, Ribas A. Primary, adaptive, and acquired resistance to cancer immunotherapy. *Cell*. 2017;168(4):707-723. doi:10.1016/j.cell.2017.01.017

Checked 7 Nov 2026. Pascual: full text read. He, Ricciuti and Sharma (first 44%): read through web-fetch summaries, not the full PDFs.
