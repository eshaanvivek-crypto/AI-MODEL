(function () {
  const form = document.getElementById('research-form');
  const questionInput = document.getElementById('question-input');
  const submitBtn = document.getElementById('submit-btn');
  const retryBtn = document.getElementById('retry-btn');
  const resetBtn = document.getElementById('reset-btn');
  const statusMessage = document.getElementById('status-message');
  const errorMessage = document.getElementById('error-message');
  const setupMessage = document.getElementById('setup-message');
  const emptyState = document.getElementById('empty-state');
  const reportPanel = document.getElementById('report-panel');
  const reportContent = document.getElementById('report-content');
  const uncertaintyMessage = document.getElementById('uncertainty-message');
  const sourcesPanel = document.getElementById('sources-panel');
  const sourcesContent = document.getElementById('sources-content');
  const stagesPanel = document.getElementById('stages-panel');
  const stagesContent = document.getElementById('stages-content');
  const warningsPanel = document.getElementById('warnings-panel');
  const warningsContent = document.getElementById('warnings-content');

  let isLoading = false;
  let lastQuestion = '';

  function resetMessages() {
    errorMessage.textContent = '';
    setupMessage.textContent = '';
    uncertaintyMessage.textContent = '';
  }

  function setLoading(loading) {
    isLoading = loading;
    submitBtn.disabled = loading;
    retryBtn.disabled = loading || !lastQuestion;
    questionInput.disabled = loading;
    statusMessage.textContent = loading ? 'Research in progress…' : 'Ready to research.';
  }

  function appendTextWithCitations(container, text, citationMap) {
    const markerPattern = /\[(\d+)\]/g;
    let index = 0;
    let match;

    while ((match = markerPattern.exec(text)) !== null) {
      const before = text.slice(index, match.index);
      if (before) {
        container.appendChild(document.createTextNode(before));
      }

      const citationId = Number(match[1]);
      const citation = citationMap.get(citationId);
      const marker = document.createElement('sup');
      if (citation) {
        const link = document.createElement('a');
        link.href = '#source-' + citationId;
        link.textContent = '[' + citationId + ']';
        link.title = citation.title;
        marker.appendChild(link);
      } else {
        marker.textContent = '[' + citationId + ']';
      }
      container.appendChild(marker);
      index = markerPattern.lastIndex;
    }

    const after = text.slice(index);
    if (after) {
      container.appendChild(document.createTextNode(after));
    }
  }

  function renderReport(report, citationMap) {
    reportContent.textContent = '';

    const lines = (report || '').split(/\r?\n/);
    let list = null;

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        list = null;
        return;
      }

      if (trimmed.startsWith('### ') || trimmed.startsWith('## ') || trimmed.startsWith('# ')) {
        list = null;
        const heading = document.createElement('h4');
        heading.textContent = trimmed.replace(/^#+\s+/, '');
        reportContent.appendChild(heading);
        return;
      }

      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!list) {
          list = document.createElement('ul');
          reportContent.appendChild(list);
        }
        const li = document.createElement('li');
        appendTextWithCitations(li, trimmed.slice(2), citationMap);
        list.appendChild(li);
        return;
      }

      list = null;
      const paragraph = document.createElement('p');
      appendTextWithCitations(paragraph, trimmed, citationMap);
      reportContent.appendChild(paragraph);
    });

    if (!reportContent.hasChildNodes()) {
      const fallback = document.createElement('p');
      fallback.textContent = 'No report generated.';
      reportContent.appendChild(fallback);
    }
  }

  function renderSources(sources) {
    sourcesContent.textContent = '';

    if (!sources.length) {
      const empty = document.createElement('p');
      empty.className = 'hint';
      empty.textContent = 'No sources were returned.';
      sourcesContent.appendChild(empty);
      return;
    }

    sources.forEach((source) => {
      const card = document.createElement('article');
      card.className = 'card';
      card.id = 'source-' + source.id;

      const title = document.createElement('h4');
      title.textContent = '[' + source.id + '] ' + (source.title || 'Untitled source');
      card.appendChild(title);

      const link = document.createElement('a');
      link.href = source.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = source.url;
      card.appendChild(link);

      const publisher = document.createElement('p');
      publisher.textContent = 'Publisher/domain: ' + (source.publisher || 'unknown');
      card.appendChild(publisher);

      const retrieved = document.createElement('p');
      const parsedDate = source.retrieved_at ? new Date(source.retrieved_at) : null;
      retrieved.textContent = 'Retrieved: ' + (parsedDate && !Number.isNaN(parsedDate.valueOf()) ? parsedDate.toLocaleString() : 'unknown');
      card.appendChild(retrieved);

      if (source.snippet) {
        const snippet = document.createElement('p');
        snippet.textContent = source.snippet;
        card.appendChild(snippet);
      }

      sourcesContent.appendChild(card);
    });
  }

  function renderStages(stages) {
    stagesContent.textContent = '';

    if (!stages.length) {
      const li = document.createElement('li');
      li.textContent = 'No stage trace available.';
      stagesContent.appendChild(li);
      return;
    }

    stages.forEach((stage) => {
      const li = document.createElement('li');
      const detail = stage.detail ? ' — ' + stage.detail : '';
      li.textContent = stage.stage + ': ' + stage.status + detail;
      stagesContent.appendChild(li);
    });
  }

  function renderWarnings(warnings) {
    warningsContent.textContent = '';

    warnings.forEach((warning) => {
      const li = document.createElement('li');
      li.textContent = warning;
      warningsContent.appendChild(li);
    });
  }

  function showResults(data) {
    const sources = Array.isArray(data.sources) ? data.sources : [];
    const citationMap = new Map(sources.map((source) => [Number(source.id), source]));

    emptyState.classList.add('hidden');
    reportPanel.classList.remove('hidden');
    sourcesPanel.classList.remove('hidden');
    stagesPanel.classList.remove('hidden');

    renderReport(data.report, citationMap);
    renderSources(sources);
    renderStages(Array.isArray(data.stages) ? data.stages : []);

    if (Array.isArray(data.warnings) && data.warnings.length) {
      warningsPanel.classList.remove('hidden');
      renderWarnings(data.warnings);
    } else {
      warningsPanel.classList.add('hidden');
      warningsContent.textContent = '';
    }

    uncertaintyMessage.textContent = data.uncertainty ? 'Uncertainty: ' + data.uncertainty : '';
    setupMessage.textContent = data.setup_error ? 'Setup notice: ' + data.setup_error : '';
  }

  async function submitQuestion(question) {
    const trimmed = question.trim();
    if (isLoading) {
      return;
    }

    if (trimmed.length < 5 || trimmed.length > 1000) {
      errorMessage.textContent = 'Question must be between 5 and 1000 characters.';
      questionInput.focus();
      return;
    }

    resetMessages();
    setLoading(true);

    try {
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed })
      });

      if (!response.ok) {
        throw new Error('Research request failed with status ' + response.status);
      }

      const data = await response.json();
      lastQuestion = trimmed;
      retryBtn.disabled = false;
      showResults(data);
      statusMessage.textContent = 'Research complete.';
    } catch (error) {
      statusMessage.textContent = 'Research failed.';
      errorMessage.textContent = error && error.message ? error.message : 'Unexpected error.';
    } finally {
      setLoading(false);
    }
  }

  function resetWorkspace() {
    form.reset();
    lastQuestion = '';
    retryBtn.disabled = true;
    setLoading(false);
    resetMessages();
    statusMessage.textContent = 'Ready to research.';
    emptyState.classList.remove('hidden');
    reportPanel.classList.add('hidden');
    sourcesPanel.classList.add('hidden');
    stagesPanel.classList.add('hidden');
    warningsPanel.classList.add('hidden');
    reportContent.textContent = '';
    sourcesContent.textContent = '';
    stagesContent.textContent = '';
    warningsContent.textContent = '';
    questionInput.focus();
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    submitQuestion(questionInput.value);
  });

  questionInput.addEventListener('keydown', function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      submitQuestion(questionInput.value);
    }
  });

  document.querySelectorAll('.example-btn').forEach((button) => {
    button.addEventListener('click', function () {
      questionInput.value = button.dataset.question || '';
      questionInput.focus();
    });
  });

  retryBtn.addEventListener('click', function () {
    if (lastQuestion) {
      questionInput.value = lastQuestion;
      submitQuestion(lastQuestion);
    }
  });

  resetBtn.addEventListener('click', resetWorkspace);
})();
