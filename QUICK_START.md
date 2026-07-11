# AIVE V2 Quick Start Guide
**New Features**: Enhanced Confidence Scoring • Professional Pipeline Progress • Research Paper Builder

---

## 🚀 Starting the System

```bash
# 1. Ensure Ollama is running
ollama list  # should show llama3:8b

# If not running:
ollama serve &

# 2. Activate Python environment and start server
cd /Users/yashchoudhary/AVIEE
.venv/bin/python app/main.py

# 3. Open browser
# Navigate to: http://localhost:5001
```

---

## ✨ Feature 1: Enhanced Confidence Scoring

### What Changed
Confidence scores now span the full 1-10 range with meaningful differentiation.

### How It Works
- **High scores (8-10)**: Multiple sources, high novelty, patents + startups
- **Medium scores (5-7)**: Good evidence, moderate novelty
- **Low scores (2-4)**: Weak evidence or incremental ideas

### What to Check
1. Run pipeline: Click "Run Pipeline" button
2. Wait for completion
3. Navigate to Canvas → Opportunities
4. Check `confidence_score` column - should see variety (not all same range)
5. Hover over scores to see breakdown

### Formula Highlights
- Evidence quality uses tiered scaling (not linear)
- High novelty (8-10) gets 40% weight + 20% boost
- Patents + startups together add 15% commercialization bonus
- Weak timing/market scores now have bigger penalties

---

## 📊 Feature 2: Professional Pipeline Progress

### What's New
Full-screen progress modal with real-time updates replaces old banner.

### How to Use
1. Click "▶ Run Pipeline" button in topbar
2. **Progress modal appears automatically**
3. Watch:
   - **3 stage markers**: Extract → Graph → Discover (with amber glow on active)
   - **Progress bar**: Smooth gradient fill with shimmer animation
   - **Live stats**: Extracted items, graph nodes, opportunities
   - **Elapsed time**: "Running for Xm Ys" counter
   - **Current item**: Shows which document is being processed
4. **Auto-closes** 10 seconds after completion (or click Close button)

### Design Details
- Amber accent color (AIVE signature)
- Pulse animations on active stage
- Subtle backdrop blur
- Updates every 2 seconds
- Persists across page reloads if pipeline still running

### What If It Gets Stuck?
- Check Status panel (Inspector → Status tab)
- Look for error messages in console
- Pipeline typically takes 2-5 minutes for 20-50 documents

---

## 📝 Feature 3: Research Paper Builder

### What It Does
Visually link knowledge nodes (opportunities, concepts, discoveries) and generate evidence-grounded research papers.

### Complete Workflow

#### Step 1: Navigate to Paper Builder
- Click **"Paper Builder"** tab in topbar
- Left panel shows available knowledge nodes grouped by type

#### Step 2: Link Knowledge Nodes
- Browse:
  - **Opportunities** (purple): Validated opportunity candidates
  - **Concepts** (blue): Technologies, problems, markets from knowledge graph
  - **Discoveries** (green): Research gaps, contradictions, method transfers
- Click **"+"** icon next to nodes to link them
- Linked nodes appear in right panel
- Click **"×"** to unlink
- Link 3-10 nodes for best results

#### Step 3: Configure Paper
- **Title**: Enter custom title (default: "Novel Insights from AIVE Discovery System")
- **Sections**: Check/uncheck sections to include:
  - ☑ Abstract
  - ☑ Introduction
  - ☑ Methods
  - ☑ Results
  - ☑ Discussion
  - ☑ Conclusion

#### Step 4: Generate Paper
- Click **"⚡ Generate Research Paper"** button
- Wait 1-2 minutes (LLM generates each section)
- Status shows: "Generating... This may take 1-2 minutes"
- Success message appears with filename
- **Auto-navigates** to Reports tab

#### Step 5: View & Download
- Paper appears in Reports tab
- Click filename to preview
- Full markdown format with:
  - All selected sections
  - Inline citations [item_id]
  - References section with source URLs
- Download or copy content as needed

### Anti-Hallucination Features
✅ **Evidence-only generation**: LLM only uses linked node content  
✅ **Citation tracking**: Every claim cites [item_id]  
✅ **Gap detection**: States explicitly when evidence insufficient  
✅ **Reference validation**: All citations tracked and verified  

### Tips for Best Results
- **Link diverse nodes**: Mix opportunities + concepts + discoveries
- **More evidence = better paper**: 5-10 linked nodes ideal
- **Check linked nodes**: Review what you linked before generating
- **Use Copilot**: Ask "What opportunities relate to X?" to find relevant nodes

---

## 🤖 Enhanced Copilot Features

### What's New
Copilot now has **intensive knowledge** of all submitted documents.

### What It Knows
- Full document summaries (not just titles)
- Problem, technology, solution fields
- Research discoveries (gaps, contradictions)
- Cross-domain connections

### How to Use

#### Research Questions
```
Q: "What technologies solve energy storage problems?"
A: [Lists relevant nodes with citations]

Q: "Show me contradictions about battery efficiency"
A: [Lists detected contradictions with source IDs]

Q: "What research gaps exist in my knowledge graph?"
A: [Lists research_gap discoveries]
```

#### Paper Generation Assistance
```
Q: "How do I generate a research paper?"
A: [Suggests Paper Builder tab with instructions]

Q: "What nodes should I link for a paper on quantum computing?"
A: [Recommends relevant opportunities and concepts]
```

#### Opportunity Discovery
```
Q: "Propose new opportunity: AI-powered solar panel optimization"
A: [Formulates, critiques, validates, stores in DB]
```

---

## 🎯 Common Workflows

### Workflow 1: Full Discovery Pipeline
```
1. Upload documents → Ingest tab (drag PDFs or paste URLs)
2. Run pipeline → Click "Run Pipeline" button
3. Watch progress → Modal shows real-time updates
4. Review opportunities → Canvas → Opportunities (sorted by confidence)
5. Generate report → Reports tab → "Generate Unified Report"
```

### Workflow 2: Research Paper Generation
```
1. Run pipeline first (need knowledge nodes)
2. Navigate to Paper Builder tab
3. Link 5-8 nodes (mix opportunities + concepts)
4. Configure title and sections
5. Generate paper (wait 1-2 min)
6. View in Reports tab
7. Download or share
```

### Workflow 3: Interactive Research Session
```
1. Ingest documents of interest
2. Run pipeline
3. Ask Copilot questions about the domain
4. Link interesting nodes in Paper Builder
5. Generate draft paper
6. Use Copilot to refine ideas
7. Re-run with updated links
```

---

## 🐛 Troubleshooting

### Pipeline Won't Start
- Check Ollama: `ollama list` should show llama3:8b
- Check server logs in terminal
- Verify port 5001 not in use: `lsof -i :5001`

### Progress Modal Stuck
- Check Inspector → Status panel for errors
- Look for last processed item name
- Pipeline may be waiting for LLM response (30-60s per item normal)

### Paper Builder Shows No Nodes
- Must run pipeline first to generate knowledge graph
- Check Canvas → Opportunities tab - should have survived opportunities
- Verify items were extracted: Canvas → Research Bank

### Generated Paper Has No Citations
- Linked nodes may lack evidence
- Try linking opportunities (they have evidence fields)
- Run validation engine to populate confidence scores

### Confidence Scores Still Similar
- May need more diverse documents
- Check source counts: papers, patents, startups
- Run pipeline multiple times - scores update with each validation pass

---

## 📊 Understanding Confidence Scores

### Score Ranges
| Range | Meaning | Typical Characteristics |
|-------|---------|------------------------|
| 9-10 | Exceptional | 5+ sources, high novelty, patents+startups, high market/timing |
| 7-8 | Highly Validated | 3-4 sources, good novelty, strong feasibility |
| 5-6 | Validated | 2-3 sources, moderate novelty, decent market fit |
| 3-4 | Partially Validated | 1-2 sources, low novelty, or weak timing |
| 1-2 | Needs Review | Minimal evidence, incremental idea, weak signals |

### What Boosts Scores
✅ Multiple diverse sources (papers + patents + startups)  
✅ High novelty score (8-10) → major boost  
✅ Patents + startups together → commercialization bonus  
✅ High market + high feasibility → synergy multiplier  
✅ Excellent timing (≥8) → urgency bonus  

### What Lowers Scores
❌ Single source or no evidence  
❌ Low novelty (<5) → reduced weight + penalty  
❌ Weak timing (<3) → 15% penalty  
❌ Weak market (<3) → 12% penalty  
❌ Low feasibility (<3) → 10% penalty  

---

## 🔍 Where to Find Things

### UI Navigation
- **Canvas Tab**: Main discovery view (Opportunities, Research Bank, Graph)
- **Simulator Tab**: Future prediction models
- **Time Machine Tab**: Workspace snapshots and history
- **Reports Tab**: Generated reports and papers
- **Paper Builder Tab**: ⭐ NEW - Visual knowledge linking + paper generation

### Inspector Panel (Right Side)
- **Copilot**: Ask questions, get answers with evidence
- **Graph**: Node/edge statistics
- **Status**: Pipeline progress, system health
- **Insights**: Discovery signals, contradictions

### Activity Bar (Left Side)
- **🎯 Discovery**: Opportunities and rejected ideas
- **📊 Knowledge**: Graph visualization (coming soon)
- **📚 Bank**: Ingested research papers/documents

---

## 💡 Pro Tips

1. **Link diverse node types** for richer papers (opportunities + concepts + discoveries)
2. **Use Copilot to explore** before linking nodes
3. **Check confidence scores** to prioritize opportunities
4. **Generate multiple papers** with different node combinations
5. **Pipeline is idempotent** - safe to run multiple times
6. **Progress modal is non-blocking** - can click elsewhere if needed
7. **Papers save to reports/** directory (also accessible via Reports tab)
8. **Citations use [item_id]** format - hover in UI to see details

---

## 📚 Next Steps

1. ✅ Run pipeline on your data
2. ✅ Check confidence score distribution
3. ✅ Watch progress modal during processing
4. ✅ Generate first research paper
5. 🎯 Ask Copilot for domain insights
6. 🎯 Iterate on paper generation with different node combinations
7. 🎯 Export papers for publication or sharing

---

## 📞 Support & Docs

- **Full Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **System Architecture**: See `PROJECT_GUIDE.md`
- **API Endpoints**: See `app/main.py` docstrings
- **Design Guidelines**: See `SKILL.md`

Enjoy the enhanced AIVE Discovery Operating System! 🚀
