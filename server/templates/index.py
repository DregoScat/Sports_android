"""
HTML Template
=============

HTML template for the web interface.
"""

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Fitness Monitor</title>
    <style>
      * {
        box-sizing: border-box;
      }
      body {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        margin: 0;
        min-height: 100vh;
        background: #0f172a;
        color: #e2e8f0;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1rem;
      }
      .panel {
        background: #1e293b;
        padding: 2rem;
        border-radius: 18px;
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.45);
        width: min(980px, 100%);
        max-width: 100%;
      }
      h1 {
        margin: 0 0 0.25rem;
        font-size: 1.8rem;
        color: #f8fafc;
      }
      .subtitle {
        color: #94a3b8;
        margin-bottom: 1.5rem;
      }
      .buttons {
        margin-bottom: 1rem;
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
      }
      button {
        border: none;
        outline: none;
        padding: 0.65rem 1.3rem;
        border-radius: 999px;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.15s ease, background 0.15s ease;
        background: #4c1d95;
        color: #f8fafc;
      }
      button:hover {
        transform: translateY(-1px);
      }
      button.active {
        background: #ec4899;
        transform: translateY(-2px);
      }
      .stream-container {
        position: relative;
        background: #020617;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
      }
      img#stream {
        width: 100%;
        min-height: 360px;
        max-height: 540px;
        object-fit: contain;
        display: block;
      }
      .meta {
        display: flex;
        justify-content: space-between;
        margin-top: 0.75rem;
        font-size: 0.9rem;
        color: #94a3b8;
        flex-wrap: wrap;
        gap: 0.5rem;
      }
      .status {
        color: #22c55e;
      }
      .status.error {
        color: #ef4444;
      }
      @media (max-width: 640px) {
        .panel {
          padding: 1rem;
        }
        h1 {
          font-size: 1.4rem;
        }
        button {
          padding: 0.5rem 1rem;
          font-size: 0.85rem;
        }
      }
    </style>
  </head>
  <body>
    <div class="panel">
      <h1>AI Fitness Monitor</h1>
      <p class="subtitle">Stream live squat or jump feedback from a single camera.</p>
      <div class="buttons">
        <button id="squat" class="active" onclick="activate('squat')">Squat Mode</button>
        <button id="jump" onclick="activate('jump')">Jump Mode</button>
      </div>
      <div class="stream-container">
        <img id="stream" src="/squat_feed" alt="Live feed" />
      </div>
      <div class="meta">
        <span id="status" class="status">Showing squat analysis</span>
        <span>Camera: auto-detected</span>
      </div>
    </div>
    <script>
      const stream = document.getElementById('stream');
      const squatBtn = document.getElementById('squat');
      const jumpBtn = document.getElementById('jump');
      const status = document.getElementById('status');

      function activate(type) {
        // Stop current stream first
        stream.src = '';
        status.className = 'status';
        
        if (type === 'squat') {
          stream.src = '/squat_feed?t=' + Date.now();
          squatBtn.classList.add('active');
          jumpBtn.classList.remove('active');
          status.textContent = 'Showing squat analysis';
        } else {
          stream.src = '/jump_feed?t=' + Date.now();
          squatBtn.classList.remove('active');
          jumpBtn.classList.add('active');
          status.textContent = 'Showing jump analysis';
        }
      }

      // Handle image errors
      stream.onerror = function() {
        status.textContent = 'Error loading stream - check camera';
        status.className = 'status error';
      };
      
      stream.onload = function() {
        console.log('Stream loaded successfully');
      };
    </script>
  </body>
</html>
"""
