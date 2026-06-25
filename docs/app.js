async function loadSiteData() {
  const response = await fetch("data/site.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Unable to load site data: ${response.status}`);
  }
  return response.json();
}

function text(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value || "";
  }
}

function renderButtons(buttons) {
  const container = document.getElementById("buttons");
  container.innerHTML = "";
  buttons.forEach((button, index) => {
    const link = document.createElement("a");
    link.href = button.href;
    link.textContent = button.label;
    if (index === 0) {
      link.className = "primary";
    }
    container.appendChild(link);
  });
}

function renderHighlights(items) {
  const container = document.getElementById("result-highlights");
  container.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "highlight-card";
    const label = document.createElement("strong");
    label.textContent = item.label;
    const value = document.createElement("span");
    value.textContent = item.value;
    card.append(label, value);
    container.appendChild(card);
  });
}

function renderSections(sections) {
  const container = document.getElementById("sections");
  container.innerHTML = "";
  sections.forEach((section) => {
    const card = document.createElement("article");
    card.className = "section-card";
    card.id = section.id;
    const title = document.createElement("h3");
    title.textContent = section.title;
    const summary = document.createElement("p");
    summary.textContent = section.summary;
    const list = document.createElement("ul");
    section.bullets.forEach((bullet) => {
      const item = document.createElement("li");
      item.textContent = bullet;
      list.appendChild(item);
    });
    const source = document.createElement("div");
    source.className = "source";
    source.textContent = `Source: ${section.source}`;
    card.append(title, summary, list, source);
    container.appendChild(card);
  });
}

function renderMedia(items) {
  const container = document.getElementById("media");
  container.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("figure");
    card.className = "media-card";
    const title = document.createElement("h3");
    title.textContent = item.title;
    const image = document.createElement("img");
    image.src = item.image;
    image.alt = item.caption;
    const caption = document.createElement("figcaption");
    caption.textContent = item.caption;
    card.append(title, image, caption);
    container.appendChild(card);
  });
}

function renderEvidence(rows) {
  const container = document.getElementById("evidence-rows");
  container.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    [row.item, row.path, row.truth].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      tr.appendChild(cell);
    });
    container.appendChild(tr);
  });
}

function renderBoundaries(boundaries) {
  const container = document.getElementById("boundaries");
  container.innerHTML = "";
  boundaries.forEach((boundary) => {
    const item = document.createElement("li");
    item.textContent = boundary;
    container.appendChild(item);
  });
}

function renderSourceFiles(sourceFiles) {
  const container = document.getElementById("source-file-groups");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  const labels = {
    package: "Package Modules",
    script: "Experiment And Figure Scripts",
    test: "Test Sources",
    entrypoint: "Root Entrypoints",
  };
  Object.keys(labels).forEach((category) => {
    const items = sourceFiles.filter((item) => item.category === category);
    if (items.length === 0) {
      return;
    }
    const group = document.createElement("section");
    group.className = "catalog-group";
    const heading = document.createElement("h3");
    heading.textContent = `${labels[category]} (${items.length})`;
    group.appendChild(heading);

    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "file-card";

      const path = document.createElement("code");
      path.textContent = item.path;

      const purpose = document.createElement("p");
      purpose.textContent = item.purpose;

      const entries = document.createElement("div");
      entries.className = "file-meta";
      const entryLabel = document.createElement("strong");
      entryLabel.textContent = "Main entries";
      const entryText = document.createElement("span");
      entryText.textContent = item.main_entries.join(", ");
      entries.append(entryLabel, entryText);

      const role = document.createElement("p");
      role.className = "paper-role";
      role.textContent = item.paper_role;

      card.append(path, purpose, entries, role);
      group.appendChild(card);
    });
    container.appendChild(group);
  });
}

function render(data) {
  document.title = data.title;
  text("venue", data.venue);
  text("title", data.title);
  text("subtitle", data.subtitle);
  text("authors", data.authors);
  text("overview", data.overview);
  text("teaser-caption", data.teaser ? data.teaser.caption : "");
  text("updated-at", `Updated ${data.updated_at}`);

  const teaser = document.getElementById("teaser-image");
  if (teaser && data.teaser) {
    teaser.src = data.teaser.image;
    teaser.alt = data.teaser.alt;
  }

  renderButtons(data.buttons);
  renderHighlights(data.result_highlights);
  renderSections(data.sections);
  renderSourceFiles(data.source_files || []);
  renderMedia(data.media_sections);
  renderEvidence(data.evidence);
  renderBoundaries(data.boundaries);
}

loadSiteData()
  .then(render)
  .catch((error) => {
    const main = document.querySelector("main");
    const message = document.createElement("p");
    message.textContent = error.message;
    message.style.color = "#b00020";
    main.prepend(message);
  });
