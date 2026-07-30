function getUserId() {
    let uid = localStorage.getItem('memora_user_id');
    if (!uid) {
        uid = 'user_' + crypto.randomUUID().replace(/-/g, '').slice(0, 16);
        localStorage.setItem('memora_user_id', uid);
    }
    return uid;
}
const USER_ID = getUserId();
const API_BASE = "http://127.0.0.1:8000/api";

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-indigo-600', 'text-white');
        btn.classList.add('text-slate-300');
    });

    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    const activeBtn = document.getElementById(`btn-${tabName}`);
    activeBtn.classList.add('bg-indigo-600', 'text-white');
    activeBtn.classList.remove('text-slate-300');

    if (tabName === 'timeline') loadTimeline();
    if (tabName === 'graph') loadGraph();
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = `<span class="text-indigo-400"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Processing with Local LLM (Ollama)...</span>`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/upload`, { method: 'POST', headers: { 'X-User-Id': USER_ID }, body: formData });
        const data = await res.json();

        if (data.success) {
            statusDiv.innerHTML = `<span class="text-emerald-400">Successfully indexed ${file.name}!</span>`;
            displayMetadataCard(data.metadata);
        } else {
            statusDiv.innerHTML = `<span class="text-rose-400">Upload failed.</span>`;
        }
    } catch (err) {
        statusDiv.innerHTML = `<span class="text-rose-400">Error connecting to backend server.</span>`;
    }
}

function displayMetadataCard(meta) {
    const resultDiv = document.getElementById('extractionResult');
    const cardsDiv = document.getElementById('metadataCards');
    resultDiv.classList.remove('hidden');

    const skills = meta.extracted_skills ? meta.extracted_skills.map(s => `<span class="bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded text-xs">${s}</span>`).join(' ') : 'None';

    cardsDiv.innerHTML = `
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
            <span class="text-xs uppercase font-bold text-indigo-400">${meta.category}</span>
            <h4 class="font-bold text-base mt-1 text-slate-100">${meta.title}</h4>
            <p class="text-xs text-slate-400 mt-2">${meta.summary}</p>
        </div>
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <div><strong class="text-slate-400">Timestamp:</strong> ${meta.date}</div>
            <div><strong class="text-slate-400">Extracted Skills:</strong> <div class="mt-1 flex flex-wrap gap-1">${skills}</div></div>
        </div>
    `;
}

async function performSearch() {
    const query = document.getElementById('searchQuery').value;
    if (!query) return;

    const container = document.getElementById('searchResults');
    container.innerHTML = `<p class="text-slate-400 text-sm"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Searching ChromaDB embeddings...</p>`;

    try {
        const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Id': USER_ID },
    body: JSON.stringify({ query })
});
        const data = await res.json();

        container.innerHTML = '';
        if (data.results.length === 0) {
            container.innerHTML = `<p class="text-slate-400 text-sm">No documents found matching query.</p>`;
            return;
        }

        data.results.forEach(r => {
            container.innerHTML += `
                <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-indigo-500/50 transition">
                    <div class="flex justify-between items-start">
                        <span class="bg-indigo-950 text-indigo-400 text-xs px-2.5 py-1 rounded-full font-semibold">${r.metadata.category}</span>
                        <span class="text-xs text-slate-500">${r.metadata.date}</span>
                    </div>
                    <h3 class="font-bold text-base mt-3 text-slate-200">${r.metadata.title}</h3>
                    <p class="text-xs text-slate-400 mt-2">${r.metadata.summary}</p>
                    <div class="mt-4 pt-3 border-t border-slate-800 flex justify-between text-xs text-slate-400">
                        <span>Skills: ${r.metadata.skills}</span>
                    </div>
                </div>
            `;
        });
    } catch (err) {
        container.innerHTML = `<p class="text-rose-400 text-sm">Search failed.</p>`;
    }
}

async function loadTimeline() {
    const container = document.getElementById('timelineContainer');
    container.innerHTML = `<p class="text-slate-400 text-sm"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Loading growth history...</p>`;

    fetch(`${API_BASE}/graph/story`, { headers: { 'X-User-Id': USER_ID } })
        .then(r => r.json())
        .then(d => {
            const storyDiv = document.getElementById('growthStory');
            if (storyDiv) storyDiv.innerHTML = `<p class="text-sm text-slate-300 leading-relaxed">${d.story}</p>`;
        });

    try {
        const res = await fetch(`${API_BASE}/timeline`, { headers: { 'X-User-Id': USER_ID } });
        const data = await res.json();

        container.innerHTML = '';

        data.timeline.forEach(item => {
            container.innerHTML += `
                <div class="relative">
                    <div class="absolute -left-[31px] top-1.5 bg-indigo-600 w-3 h-3 rounded-full ring-4 ring-slate-950"></div>
                    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                        <span class="text-xs font-bold text-indigo-400">${item.date || 'Undated'}</span>
                        <h4 class="font-bold text-base text-slate-200 mt-0.5">${item.label}</h4>
                        <p class="text-xs text-slate-400 mt-1">${item.summary || ''}</p>
                    </div>
                </div>
            `;
        });
    } catch (err) {
        container.innerHTML = `<p class="text-rose-400 text-sm">Failed to load timeline.</p>`;
    }
}

async function handleResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const resultDiv = document.getElementById('resumeResult');
    resultDiv.classList.remove('hidden');
    resultDiv.innerHTML = `<p class="text-slate-400 text-sm text-center"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Analyzing resume metrics...</p>`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/resume/evaluate`, { method: 'POST', headers: { 'X-User-Id': USER_ID }, body: formData });
        const evalData = data.evaluation;

        const feedbackList = evalData.feedback.map(f => `<li class="text-xs text-slate-300">• ${f}</li>`).join('');

        resultDiv.innerHTML = `
            <div class="flex items-center justify-between pb-6 border-b border-slate-800">
                <div>
                    <h3 class="text-lg font-bold">${data.filename}</h3>
                    <p class="text-xs text-slate-400">Automated System Score</p>
                </div>
                <div class="text-4xl font-extrabold text-amber-400 bg-amber-950/50 border border-amber-800 px-4 py-2 rounded-2xl">
                    ${evalData.score}<span class="text-sm text-amber-500 font-normal">/100</span>
                </div>
            </div>
            <div class="mt-6 space-y-4">
                <h4 class="font-semibold text-sm text-slate-200">System Feedback & Recommendations:</h4>
                <ul class="space-y-2">${feedbackList}</ul>
            </div>
        `;
    } catch (err) {
        resultDiv.innerHTML = `<p class="text-rose-400 text-sm">Resume analysis failed.</p>`;
    }
}
function loadGraph() {
    const svg = d3.select('#graphSvg');
    svg.selectAll('*').remove();

    const container = document.getElementById('graphSvg').parentElement;
    const width = container.clientWidth;
    const height = container.clientHeight;

    fetch(`${API_BASE}/graph`, { headers: { 'X-User-Id': USER_ID } })
        .then(res => res.json())
        .then(data => renderGraph(data, svg, width, height))
        .catch(() => {
            svg.append('text').attr('x', 20).attr('y', 40).attr('fill', '#f87171').text('Failed to load graph.');
        });
}

function renderGraph(data, svg, width, height) {
    if (!data.nodes || data.nodes.length === 0) {
        svg.append('text').attr('x', 20).attr('y', 40).attr('fill', '#94a3b8').text('No graph data yet. Upload some documents first!');
        return;
    }

    const nodes = data.nodes.map(n => ({ ...n }));
    const links = data.links.map(l => ({ ...l }));
    const causalTypes = ['LED_TO', 'BUILT_ON', 'APPLIED_IN'];

    const g = svg.attr('viewBox', [0, 0, width, height])
        .call(d3.zoom().scaleExtent([0.3, 3]).on('zoom', (e) => g.attr('transform', e.transform)))
        .append('g');

    const linkSel = g.append('g').selectAll('line').data(links).join('line')
        .attr('stroke', d => causalTypes.includes(d.relationship) ? '#fbbf24' : '#475569')
        .attr('stroke-width', d => causalTypes.includes(d.relationship) ? 2.5 : 1)
        .attr('stroke-dasharray', d => d.relationship === 'USES_SKILL' ? '4,3' : null)
        .attr('opacity', 0.7);

    const nodeSel = g.append('g').selectAll('circle').data(nodes).join('circle')
        .attr('r', d => d.type === 'Skill' ? 8 : 14)
        .attr('fill', d => d.type === 'Skill' ? '#22d3ee' : '#6366f1')
        .attr('stroke', '#0f172a')
        .attr('stroke-width', 2)
        .on('mouseover', showTooltip)
        .on('mousemove', moveTooltip)
        .on('mouseout', hideTooltip);

    const labelSel = g.append('g').selectAll('text').data(nodes).join('text')
        .text(d => d.label)
        .attr('font-size', 10)
        .attr('fill', '#cbd5e1')
        .attr('dx', 16)
        .attr('dy', 4)
        .style('pointer-events', 'none');

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(90).strength(0.4))
        .force('charge', d3.forceManyBody().strength(-220))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide(24))
        .on('tick', () => {
            linkSel.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                   .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
            nodeSel.attr('cx', d => d.x).attr('cy', d => d.y);
            labelSel.attr('x', d => d.x).attr('y', d => d.y);
        });

    nodeSel.call(dragBehavior(simulation));
}

function dragBehavior(simulation) {
    return d3.drag()
        .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; });
}

function showTooltip(event, d) {
    const tip = document.getElementById('graphTooltip');
    tip.classList.remove('hidden');
    tip.innerHTML = d.type === 'Skill'
        ? `<strong class="text-cyan-400">${d.label}</strong><br><span class="text-slate-400">Skill node</span>`
        : `<strong class="text-indigo-400">${d.label}</strong><br><span class="text-slate-400">${d.type || ''} · ${d.date || ''}</span><br><span class="text-slate-300">${d.summary || ''}</span>`;
    moveTooltip(event);
}
function moveTooltip(event) {
    const tip = document.getElementById('graphTooltip');
    const rect = document.getElementById('graphSvg').parentElement.getBoundingClientRect();
    tip.style.left = (event.clientX - rect.left + 15) + 'px';
    tip.style.top = (event.clientY - rect.top + 15) + 'px';
}
function hideTooltip() {
    document.getElementById('graphTooltip').classList.add('hidden');
}