# Papers to download by hand (2026-11-17 batch, shared by Damir)

These need a subscription or block scripts. Open the link (with your IRB login), download the PDF and
save it under exactly the path given; the next weekly run writes the notes. The pages list them as "PDF missing".

| # | Paper | Open | Save as |
|---|---|---|---|
| 3 | Cave evolution on repeat: reuse of the same genomic regions across lineages of Astyanax me | https://doi.org/10.1093/genetics/iyag223 | `papers/amexicanus/Richards_2026_Genetics_cave_evolution_on_repeat.pdf` |
| 7 | LncRNA-BERT: an RNA language model for classifying coding and long non-coding RNA | https://doi.org/10.1080/09540091.2026.2624131 | `papers/general/Romeijn_2026_ConnectSci_LncRNA-BERT.pdf` |
| 9 | Toward generalizable and interpretable AI in regulatory genomics | https://doi.org/10.1038/s41588-026-02670-3 | `papers/regulatiory_genomics/Nagai_2026_NatGenet_AI_in_regulatory_genomics.pdf` |
| 11 | ENCODE GRAMMAR: A deep learning model resource for decoding the DNA sequence logic of regu | https://doi.org/10.5281/zenodo.21795359 | `papers/regulatiory_genomics/Yun_2026_Zenodo_ENCODE_GRAMMAR.pdf` |
| 15 | Obtaining genetics insights from deep learning via explainable artificial intelligence | https://doi.org/10.1038/s41576-022-00532-2 | `papers/regulatiory_genomics/Novakovsky_2022_NatRevGenet_explainable_AI_genomics.pdf` |
| 20 | Transcriptomic profiling reveals tetrabromobisphenol A-induced dysregulation of hepatic li | https://doi.org/10.1016/j.cbpc.2025.110336 | `papers/drerio/Li_2026_CBPC_TBBPA_carp_hepatic_lipids.pdf` |
| 21 | Highly accurate ab initio gene annotation with ANNEVO | https://doi.org/10.1038/s41592-026-03036-7 | `papers/general/Zhang_2026_NatMethods_ANNEVO_gene_annotation.pdf` |
| 22 | RAF1 mutations in childhood-onset dilated cardiomyopathy | https://doi.org/10.1038/ng.2963 | `papers/general/Dhandapany_2014_NatGenet_RAF1_dilated_cardiomyopathy.pdf` |
| 23 | An atlas of transcribed enhancers across helper T cell diversity for decoding human diseas | https://doi.org/10.1126/science.add8394 | `papers/regulatiory_genomics/Oguchi_2024_Science_transcribed_enhancers_T_cells.pdf` |
| 25 | Fish models for investigating nutritional regulation of embryonic development | https://doi.org/10.1016/j.ydbio.2021.03.012 | `papers/drerio/Riddle_2021_DevBiol_fish_nutrition_embryo_development.pdf` |
| 28 | Protist genomics: key to understanding eukaryotic evolution | https://doi.org/10.1016/j.tig.2025.05.004 | `papers/general/Schoenle_2025_TrendsGenet_protist_genomics.pdf` |
| 29 | Epigenetic regulation in early embryo development: from zygotic genome activation to the f | https://doi.org/10.1016/j.tig.2025.05.005 | `papers/drerio/Xu_2025_TrendsGenet_epigenetics_ZGA_to_lineage.pdf` |
| 30 | Evolutionary causes and consequences of gene duplication | https://doi.org/10.1038/s41576-026-00935-5 | `papers/general/Cisneros_2026_NatRevGenet_gene_duplication.pdf` |
| 31 | Predicting expression-altering promoter mutations with deep learning | https://doi.org/10.1126/science.ads7373 | `papers/regulatiory_genomics/Jaganathan_2025_Science_promoter_mutations_deep_learning.pdf` |
| 33 | Elucidating the coordination of RNA processing using short-read and long-read RNA-sequenci | https://doi.org/10.1038/s41580-025-00895-4 | `papers/general/AlfonsoGonzalez_2025_NatRevMCB_RNA_processing_sequencing.pdf` |
| 36 | Modelling and design of transcriptional enhancers | https://doi.org/10.1038/s44222-025-00280-y | `papers/regulatiory_genomics/DeWinter_2025_NatRevBioeng_enhancer_modelling_design.pdf` |
| 37 | Coordinating tissue development to build body and brain: Lessons from the gastrula organis | https://doi.org/10.1016/j.cdev.2025.204042 | `papers/drerio/Neaverson_2025_CellsDev_gastrula_organiser.pdf` |

Notes:
- 3 (Richards, Genetics): the bioRxiv preprint is kept in papers/_superseded_preprints/; get the Genetics version (PMC13643756 is not open yet).
- 11 (ENCODE GRAMMAR): Zenodo record; Zenodo blocks this server's network, download from a browser.

## Status update 2026-11-17 (afternoon)

Marta downloaded 13 of these into Drive folder 1KdPIho1Xp6Tb_KFvK8bxJDX1ANz4gnFU; filed with
`14_fetch_drive_folder.py` + `15_add_local_pdfs.py` (batch 2026-11-17_damir_manual).

- 3 Richards: no access to Genetics -> notes from the bioRxiv v1 preprint
  (`papers/amexicanus/Richards_2026_bioRxiv_QTL_repeatability_cave_traits.pdf`); page shows a source note.
- 29 Xu 2025 and 31 Jaganathan 2025: no access -> notes from the public abstract/metadata only
  (`.txt` sources made by `16_make_abstract_source.py`); page shows "Not the full paper".
- **Still missing: 20 Li 2026 (TBBPA, common carp), https://doi.org/10.1016/j.cbpc.2025.110336**
  -> save as `papers/drerio/Li_2026_CBPC_TBBPA_carp_hepatic_lipids.pdf`
