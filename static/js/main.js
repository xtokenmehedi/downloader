let activeTask = null;

async function startDL() {
    const url = document.getElementById('url').value;
    if(!url) return;

    const btn = document.getElementById('dlBtn');
    btn.disabled = true;
    btn.innerText = "Processing...";

    const res = await fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            url: url,
            format: document.getElementById('format').value,
            limit: document.getElementById('limit').value
        })
    });
    
    const data = await res.json();
    activeTask = data.tid;
    log(`Job started. Task ID: ${activeTask}`);
    
    const poll = setInterval(async () => {
        const sRes = await fetch(`/api/status/${activeTask}`);
        const sData = await sRes.json();

        sData.logs.forEach(msg => log(msg));
        document.getElementById('progress').style.width = sData.progress;
        document.getElementById('stats').innerText = `Speed: ${sData.speed} | ETA: ${sData.eta}`;

        if(sData.status === 'completed' || sData.status === 'failed') {
            clearInterval(poll);
            btn.disabled = false;
            btn.innerText = "Start Download";
            new Notification("Download Finished!");
        }
    }, 1000);
}

function log(msg) {
    const term = document.getElementById('terminal');
    term.innerHTML += `<div>> ${msg}</div>`;
    term.scrollTop = term.scrollHeight;
}