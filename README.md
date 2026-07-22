# Build an AI Business Copilot 🏔️

A hands-on Codecademy workshop where you build a **practical GenAI business copilot**
from scratch — for a fictional outdoor retailer, **Trailhead Supply Co.**

By the end you'll have a working copilot that can answer both:

- **Policy questions** — _"What's the return window on hiking boots?"_ — by searching the
  company's documents (Retrieval-Augmented Generation, or **RAG**), and
- **Account questions** — _"Where is order #1027?"_ — by looking up real business data.

You'll learn *why* each piece exists and *how* to customize the templates for your own
use case. **No prior Python experience required** — you'll run cells, edit configuration,
and tweak prompts.

---

## What you'll build (2 evenings, ~6 hours)

| Notebook | Session | You'll learn to… |
| --- | --- | --- |
| `01_intro_genai_business.ipynb` | 1 · hr 1 | Call Claude, write good prompts, and see the copilot's overall architecture |
| `02_documents_to_knowledge.ipynb` | 1 · hr 2 | Turn business documents into a searchable knowledge base (chunking, embeddings, FAISS) |
| `03_rag_qa_flow.ipynb` | 1 · hr 3 | Combine retrieval + Claude into a grounded, cited Q&A copilot |
| `04_structured_business_data.ipynb` | 2 · hr 1 | Answer questions from real order/inventory data using tool use (function calling) |
| `05_routing_workflows.ipynb` | 2 · hr 2 | Route each question to the right workflow — documents vs. data |
| `06_reliability_and_review.ipynb` | 2 · hr 3 | Evaluate, harden, and cost-optimize the copilot; extension ideas |

---

## Before you start

You need two things:

1. A **Google account** (to run notebooks in [Google Colab](https://colab.research.google.com/)).
2. An **Anthropic API key** — create one at <https://console.anthropic.com/>.

## Running the notebooks

**In Google Colab (recommended):** open a notebook from the `notebooks/` folder in Colab
and run the cells top to bottom. The first cell installs everything and prompts for your
API key (entered securely — it is never saved in the notebook).

---

## Repository layout

```
trailhead-copilot/
├── notebooks/     # the workshop, notebook by notebook (the main material)
├── data/          # Trailhead's business data as CSVs (customers, orders, inventory, …)
├── documents/     # company policies & FAQs — markdown/ (readable) and pdf/ (for parsing)
├── src/           # trailhead.py: small shared helpers the notebooks reuse
├── scripts/       # generate_assets.py: regenerates the data + PDFs (instructor use)
└── images/        # architecture diagrams
```

## About the data

Trailhead Supply Co. is entirely fictional. All customers, orders, and documents are
generated and **internally consistent** — every order references a real customer and
products, every shipment references a real order, and the policy documents describe the
exact rules the data follows. To regenerate everything (deterministically):

```bash
pip install fpdf2 markdown      # only needed to re-render the PDFs
python scripts/generate_assets.py
```
