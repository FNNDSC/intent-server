# Intent-Action Service papers build system (factory-style)
# Uses a single document factory to produce HTML, LaTeX, PDF, and DOCX.

BUILD_DIR := build
LATEX_TEMPLATE := latex/academic-template.tex
PDF_ENGINE ?= tectonic
TECTONIC_CACHE_DIR ?= $(HOME)/.cache/Tectonic
TECTONIC_FMT_GLOB := $(TECTONIC_CACHE_DIR)/formats/*.fmt

COMMON_PANDOC_FLAGS := -V lang=en -V geometry:margin=1in -V fontsize=11pt

.PHONY: all papers clean help

all: paper_research paper_engineering engineering_brief agentic-nondeterminism experiment

papers: all

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Document factory
define build_document
$(1)_SRC := $(2)
$(1)_DIR := $(BUILD_DIR)
$(1)_RESOURCE_PATH ?= $(dir $(2)):$(BUILD_DIR):.
$(1)_ADOC_ATTRS ?= -a data-uri -a allow-uri-read
$(1)_HTML_ATTRS ?= $$($(1)_ADOC_ATTRS)
$(1)_DOCBOOK := $$($(1)_DIR)/$(1).xml
$(1)_HTML := $$($(1)_DIR)/$(1).html
$(1)_DOCX := $$($(1)_DIR)/$(1).docx
$(1)_TEX := $$($(1)_DIR)/$(1).tex
$(1)_PDF := $$($(1)_DIR)/$(1).pdf
$(1)_PANDOC_FLAGS ?= $(COMMON_PANDOC_FLAGS)

.PHONY: $(1) $(1)-html $(1)-pdf $(1)-docx

$(1): $(1)-html $(1)-pdf $(1)-docx

$$($(1)_HTML): $$($(1)_SRC) | $(BUILD_DIR)
	asciidoctor $$($(1)_HTML_ATTRS) -o $$@ $$<

$(1)-html: $$($(1)_HTML)

$$($(1)_DOCBOOK): $$($(1)_SRC) | $(BUILD_DIR)
	asciidoctor $$($(1)_ADOC_ATTRS) -b docbook -o $$@ $$<

ifneq ($$($(1)_SKIP_TEX_RULE),1)
$$($(1)_TEX): $$($(1)_DOCBOOK) $(LATEX_TEMPLATE) | $(BUILD_DIR)
	@if command -v pandoc >/dev/null 2>&1; then \
		pandoc $$< -f docbook -t latex --template=$(LATEX_TEMPLATE) --resource-path=$$($(1)_RESOURCE_PATH) $$($(1)_PANDOC_FLAGS) -o $$@; \
	else \
		echo "pandoc not installed; cannot generate $$@"; exit 1; \
	fi
endif

$$($(1)_PDF): $$($(1)_TEX) | $(BUILD_DIR)
	@if command -v $(PDF_ENGINE) >/dev/null 2>&1; then \
		if [ "$(PDF_ENGINE)" = "tectonic" ]; then \
			$(PDF_ENGINE) --keep-logs --keep-intermediates --outdir=$(BUILD_DIR) $$<; \
		else \
			$(PDF_ENGINE) -interaction=nonstopmode -output-directory=$(BUILD_DIR) $$<; \
		fi; \
	else \
		echo "PDF engine $(PDF_ENGINE) not found; LaTeX left at $$<"; \
	fi

$(1)-pdf: $$($(1)_PDF)

$$($(1)_DOCX): $$($(1)_DOCBOOK) | $(BUILD_DIR)
	@if command -v pandoc >/dev/null 2>&1; then \
		pandoc $$< -f docbook -t docx --resource-path=$$($(1)_RESOURCE_PATH) -o $$@; \
	else \
		echo "pandoc not installed; skipping $$@"; \
	fi

$(1)-docx: $$($(1)_DOCX)

endef

# Document instantiations
paper_research_PANDOC_FLAGS := $(COMMON_PANDOC_FLAGS)
paper_engineering_PANDOC_FLAGS := $(COMMON_PANDOC_FLAGS)
engineering_brief_PANDOC_FLAGS := $(COMMON_PANDOC_FLAGS)
agentic-nondeterminism_PANDOC_FLAGS := $(COMMON_PANDOC_FLAGS) -V documentclass=IEEEtran -V classoption=onecolumn -V bibliography=agentic-nondeterminism
agentic-nondeterminism_ADOC_ATTRS := -a data-uri -a allow-uri-read -a stem=latexmath
agentic-nondeterminism_SKIP_TEX_RULE := 1
experiment_PANDOC_FLAGS := $(COMMON_PANDOC_FLAGS) -V documentclass=IEEEtran -V classoption=onecolumn
experiment_ADOC_ATTRS := -a data-uri -a allow-uri-read -a stem=latexmath

$(eval $(call build_document,paper_research,paper-research/main.adoc))
$(eval $(call build_document,paper_engineering,paper-engineering/main.adoc))
$(eval $(call build_document,engineering_brief,engineering-brief/main.adoc))
$(eval $(call build_document,agentic-nondeterminism,agentic-nondeterminism/LLM-to-IAS.adoc))
$(eval $(call build_document,experiment,agentic-nondeterminism/experiment.adoc))

# Ensure BibTeX database is available in build/ for agentic-nondeterminism
build/agentic-nondeterminism.bib: agentic-nondeterminism/agentic-nondeterminism.bib | $(BUILD_DIR)
	cp $< $@

# Override LaTeX build for agentic-nondeterminism to fix escaped citations
build/agentic-nondeterminism.tex: build/agentic-nondeterminism.xml $(LATEX_TEMPLATE) build/agentic-nondeterminism.bib | $(BUILD_DIR)
	@if command -v pandoc >/dev/null 2>&1; then \
		pandoc build/agentic-nondeterminism.xml -f docbook -t latex --template=$(LATEX_TEMPLATE) --resource-path=$(agentic-nondeterminism_RESOURCE_PATH) $(agentic-nondeterminism_PANDOC_FLAGS) -o $@; \
		agentic-nondeterminism/fix_cites.py $@; \
	else \
		echo "pandoc not installed; cannot generate $@"; exit 1; \
	fi

tectonic-cache:
	@mkdir -p $(BUILD_DIR)/.tectonic-check
	@echo "\\documentclass{article}\\begin{document}cache\\end{document}" > $(BUILD_DIR)/.tectonic-check/cache.tex
	@echo "Warming Tectonic cache under $(TECTONIC_CACHE_DIR)..."
	@TECTONIC_BUNDLE_PATH=$(TECTONIC_CACHE_DIR) $(PDF_ENGINE) --keep-logs --keep-intermediates $(BUILD_DIR)/.tectonic-check/cache.tex >/dev/null || true
	@if ls $(TECTONIC_FMT_GLOB) >/dev/null 2>&1; then \
		echo "Tectonic cache ready at $(TECTONIC_CACHE_DIR)."; \
	else \
		echo "Tectonic cache not found (needs network)."; \
		exit 1; \
	fi

clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "Build targets:"
	@echo "  all / papers                Build all documents (HTML, LaTeX, PDF, DOCX)"
	@echo "  paper_research              Research paper outputs in build/"
	@echo "  paper_engineering           Engineering paper outputs in build/"
	@echo "  engineering_brief           Brief outputs in build/"
	@echo "  agentic-nondeterminism      Agentic nondeterminism paper outputs in build/"
	@echo "  experiment                  ChRIS experiment plan outputs in build/"
	@echo "  tectonic-cache              Warm/download Tectonic bundle cache"
	@echo "Variables:"
	@echo "  PDF_ENGINE=tectonic|pdflatex   PDF engine used for LaTeX compilation"
