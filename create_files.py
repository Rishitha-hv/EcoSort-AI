from pathlib import Path
import zipfile, textwrap

root = Path(__file__).resolve().parent / "EcoSort_AI_Corrected"
(root / "templates").mkdir(parents=True, exist_ok=True)
(root / "static" / "css").mkdir(parents=True, exist_ok=True)

content = {}

content["templates/base.html"] = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}EcoSort AI{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
<header class="site-header">
  <a class="brand" href="{{ url_for('home') }}"><span class="brand-mark">♻</span><span>EcoSort <b>AI</b></span></a>
  <button class="menu-toggle" type="button" onclick="document.querySelector('.main-nav').classList.toggle('open')">☰</button>
  <nav class="main-nav">
    <a class="{% if request.endpoint == 'home' %}active{% endif %}" href="{{ url_for('home') }}">Home</a>
    <a class="{% if request.endpoint in ['classify','camera','video'] %}active{% endif %}" href="{{ url_for('classify') }}">Classify</a>
    <a class="{% if request.endpoint == 'history' %}active{% endif %}" href="{{ url_for('history') }}">History</a>
    <a class="{% if request.endpoint == 'reports' %}active{% endif %}" href="{{ url_for('reports') }}">Report</a>
  </nav>
</header>
<main class="page-shell">
  {% with messages = get_flashed_messages() %}
    {% if messages %}<div class="flash-wrap">{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}</div>{% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</main>
<footer class="footer"><strong>♻ EcoSort AI</strong><span>Smarter waste sorting for a cleaner tomorrow.</span></footer>
</body>
</html>
'''

content["templates/index.html"] = r'''{% extends "base.html" %}
{% block title %}EcoSort AI | Home{% endblock %}
{% block content %}
<section class="home-hero">
  <div class="hero-copy">
    <span class="eyebrow">SMART WASTE CLASSIFICATION</span>
    <h1>Sort smarter.<br><span>Live greener.</span></h1>
    <p>Identify recyclable waste in seconds with AI-powered image classification. A simple step towards a cleaner planet.</p>
    <a class="btn btn-light" href="{{ url_for('classify') }}">Get Started <span>→</span></a>
    <div class="hero-note">● Four waste categories · Instant AI prediction</div>
  </div>
  <div class="hero-art"><div class="orbit"></div><div class="orbit orbit-two"></div><div class="earth">♻</div><span class="leaf leaf-a">✦</span><span class="leaf leaf-b">❧</span><div class="art-caption">Make every item count</div></div>
</section>
<section class="section-heading"><div><span class="eyebrow green-text">EXPLORE ECOSORT</span><h2>What can we classify?</h2><p>Our model recognises four common recyclable material categories.</p></div><a class="text-link" href="{{ url_for('classify') }}">Start classifying →</a></section>
<section class="category-grid">
  <article class="category-card"><div class="category-icon glass-icon">◇</div><h3>Glass</h3><p>Bottles and glass containers</p></article>
  <article class="category-card"><div class="category-icon metal-icon">▤</div><h3>Metal</h3><p>Cans and metal packaging</p></article>
  <article class="category-card"><div class="category-icon paper-icon">▧</div><h3>Paper</h3><p>Sheets, newspapers and paper</p></article>
  <article class="category-card"><div class="category-icon plastic-icon">♧</div><h3>Plastic</h3><p>Bottles and plastic containers</p></article>
</section>
<div class="home-cta"><div><span class="eyebrow green-text">READY TO BEGIN?</span><h2>Give your waste a second chance.</h2></div><a class="btn btn-primary" href="{{ url_for('classify') }}">Classify an item →</a></div>
{% endblock %}'''

content["templates/classify.html"] = r'''{% extends "base.html" %}
{% block title %}Classify | EcoSort AI{% endblock %}
{% block content %}
<section class="page-intro"><span class="eyebrow green-text">AI-POWERED ANALYSIS</span><h1>Classify Waste Item</h1><p>Choose how you want to submit an item for classification.</p></section>
<section class="input-options">
  <article class="input-card featured"><div class="option-icon">↑</div><span class="option-tag">IMAGE</span><h2>Upload Image</h2><p>Select a clear JPG, PNG or JPEG photo containing one waste item.</p>
    <form method="POST" action="{{ url_for('classify') }}" enctype="multipart/form-data">
      <label class="file-drop"><input type="file" name="image" accept=".jpg,.jpeg,.png" required><b>Choose an image</b><small>JPG, JPEG or PNG</small></label>
      <button class="btn btn-primary full" type="submit">Analyse Image →</button>
    </form>
  </article>
  <article class="input-card"><div class="option-icon camera-icon">◎</div><span class="option-tag">LIVE</span><h2>Use Camera</h2><p>Capture a waste item directly using your device camera.</p><div class="option-spacer"></div><a class="btn btn-outline full" href="{{ url_for('camera') }}">Open Camera →</a></article>
  <article class="input-card"><div class="option-icon video-icon">▷</div><span class="option-tag">VIDEO</span><h2>Upload Video</h2><p>Sample video frames and classify the visible waste item.</p><div class="option-spacer"></div><a class="btn btn-outline full" href="{{ url_for('video') }}">Upload Video →</a></article>
</section>
<div class="notice">ⓘ <p><b>For best results:</b> Use a well-lit image with one clearly visible object. Supported categories are glass, metal, paper and plastic. Other objects may be marked as unknown.</p></div>
{% endblock %}'''

content["templates/camera.html"] = r'''{% extends "base.html" %}
{% block title %}Camera | EcoSort AI{% endblock %}
{% block content %}
<section class="page-intro"><span class="eyebrow green-text">LIVE CAPTURE</span><h1>Use Your Camera</h1><p>Place one waste item in view and capture a clear image.</p></section>
<div class="camera-panel">
  <video id="cameraPreview" autoplay playsinline></video><canvas id="cameraCanvas" hidden></canvas>
  <div class="camera-actions"><button class="btn btn-outline" type="button" id="startCamera">Start camera</button><button class="btn btn-primary" type="button" id="captureButton">Capture image</button></div>
  <form method="POST" action="{{ url_for('camera') }}" id="cameraForm"><input type="hidden" name="camera_image" id="cameraImage"><button class="btn btn-primary full" type="submit">Classify captured image →</button></form>
  <p class="muted" id="cameraStatus">Allow camera access when your browser asks.</p>
</div>
<script>
const video=document.getElementById('cameraPreview'),canvas=document.getElementById('cameraCanvas');let stream=null;
document.getElementById('startCamera').addEventListener('click',async()=>{try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});video.srcObject=stream;document.getElementById('cameraStatus').textContent='Camera is ready.';}catch(e){document.getElementById('cameraStatus').textContent='Camera access failed. Check browser permissions.';}});
document.getElementById('captureButton').addEventListener('click',()=>{if(!video.videoWidth){document.getElementById('cameraStatus').textContent='Start the camera first.';return;}canvas.width=video.videoWidth;canvas.height=video.videoHeight;canvas.getContext('2d').drawImage(video,0,0);document.getElementById('cameraImage').value=canvas.toDataURL('image/jpeg',0.9);document.getElementById('cameraStatus').textContent='Image captured. Click classify to continue.';});
document.getElementById('cameraForm').addEventListener('submit',e=>{if(!document.getElementById('cameraImage').value){e.preventDefault();document.getElementById('cameraStatus').textContent='Capture an image first.';}});
window.addEventListener('beforeunload',()=>{if(stream)stream.getTracks().forEach(t=>t.stop());});
</script>
{% endblock %}'''

content["templates/video.html"] = r'''{% extends "base.html" %}
{% block title %}Video | EcoSort AI{% endblock %}
{% block content %}
<section class="page-intro"><span class="eyebrow green-text">VIDEO ANALYSIS</span><h1>Upload a Video</h1><p>EcoSort AI samples selected frames and classifies each frame independently.</p></section>
<div class="form-panel narrow"><div class="large-option-icon">▷</div>
<form method="POST" action="{{ url_for('video') }}" enctype="multipart/form-data">
<label class="file-drop big-drop"><input type="file" name="video" accept=".mp4,.avi,.mov,.mkv" required><b>Choose a video</b><small>MP4, AVI, MOV or MKV</small></label>
<button class="btn btn-primary full" type="submit">Analyse video →</button></form>
<p class="muted center">For faster processing, use a short video with a clearly visible waste item.</p></div>
{% endblock %}'''

content["templates/result.html"] = r'''{% extends "base.html" %}
{% block title %}Result | EcoSort AI{% endblock %}
{% block content %}
<section class="page-intro"><span class="eyebrow green-text">ANALYSIS COMPLETE</span><h1>Classification Result</h1><p>Here is the prediction generated by EcoSort AI.</p></section>
<div class="result-layout"><div class="result-image"><img src="{{ image_url }}" alt="Analysed waste item"></div>
<div class="result-card"><span class="eyebrow green-text">PREDICTED CATEGORY</span>
<div class="prediction-name {% if predicted_class|lower in ['unknown','unknown item'] %}unknown{% endif %}">{{ predicted_class|title }}</div>
<p class="muted">Model confidence</p><div class="confidence-number">{{ '%.2f'|format(confidence) }}<small>%</small></div>
<div class="progress"><span style="width:{{ confidence }}%"></span></div>
<p class="result-explain">{% if predicted_class|lower in ['unknown','unknown item'] %}The image did not meet the confidence and separation requirements for a supported category.{% else %}The item was classified as {{ predicted_class }}.{% endif %}</p>
<a class="btn btn-primary full" href="{{ url_for('classify') }}">Classify another item →</a><a class="text-link centered-link" href="{{ url_for('history') }}">View classification history</a></div></div>
{% endblock %}'''

content["templates/video_result.html"] = r'''{% extends "base.html" %}
{% block title %}Video Results | EcoSort AI{% endblock %}
{% block content %}
<section class="page-intro"><span class="eyebrow green-text">VIDEO ANALYSIS COMPLETE</span><h1>Frame Classification Results</h1><p>Summary of the sampled frames from your video.</p></section>
<section class="stats-grid three"><div class="stat-card"><span>Frames analysed</span><strong>{{ total_frames }}</strong></div><div class="stat-card"><span>Recognised frames</span><strong>{{ recognised_count }}</strong></div><div class="stat-card"><span>Unknown frames</span><strong>{{ unknown_count }}</strong></div></section>
{% if results %}<div class="frame-grid">{% for item in results %}<article class="frame-card"><img src="{{ item.image_url }}" alt="Video frame {{ item.frame_number }}"><div class="frame-info"><b>Frame {{ item.frame_number }}</b><span class="class-pill {% if item.prediction|lower in ['unknown','unknown item'] %}unknown{% endif %}">{{ item.prediction|title }}</span><small>{{ '%.2f'|format(item.confidence) }}% confidence</small></div></article>{% endfor %}</div>{% else %}<div class="empty-state"><h2>No frames were analysed</h2><p>Try a longer or different video.</p></div>{% endif %}
<a class="btn btn-primary" href="{{ url_for('video') }}">Analyse another video →</a>
{% endblock %}'''

content["templates/history.html"] = r'''{% extends "base.html" %}
{% block title %}History | EcoSort AI{% endblock %}
{% block content %}
<section class="page-intro split-intro"><div><span class="eyebrow green-text">YOUR ACTIVITY</span><h1>Classification History</h1><p>Review the items analysed by EcoSort AI.</p></div><form method="POST" action="{{ url_for('clear_history') }}" onsubmit="return confirm('Clear all classification history?')"><button class="btn btn-danger" type="submit">Clear history</button></form></section>
<div class="table-card">
{% if records %}<div class="table-scroll"><table><thead><tr><th>Item</th><th>Prediction</th><th>Confidence</th><th>Source</th><th>Date & time</th></tr></thead><tbody>
{% for item in records %}<tr><td><div class="item-cell"><img src="{{ url_for('uploaded_file', filename=item['filename']) }}" alt=""><span>{{ item['filename'] }}</span></div></td><td><span class="class-pill {% if item['waste_type']|lower in ['unknown','unknown item'] %}unknown{% endif %}">{{ item['waste_type']|title }}</span></td><td><div class="table-confidence"><b>{{ '%.1f'|format(item['confidence']) }}%</b><div class="mini-progress"><i style="width:{{ item['confidence'] }}%"></i></div></div></td><td>{{ item['source']|title }}</td><td>{{ item['timestamp'] }}</td></tr>{% endfor %}
</tbody></table></div>{% else %}<div class="empty-state"><div>♻</div><h2>No classifications yet</h2><p>Your analysed items will appear here.</p><a class="btn btn-primary" href="{{ url_for('classify') }}">Classify your first item</a></div>{% endif %}
</div>
{% endblock %}'''

content["templates/reports.html"] = r'''{% extends "base.html" %}
{% block title %}Reports | EcoSort AI{% endblock %}
{% block content %}
<section class="page-intro"><span class="eyebrow green-text">ANALYTICS OVERVIEW</span><h1>Classification Report</h1><p>A summary of your waste classification activity.</p></section>
<section class="stats-grid three"><div class="stat-card"><span>Total analyses</span><strong>{{ total }}</strong></div><div class="stat-card"><span>Recognised items</span><strong>{{ total - unknown_count }}</strong></div><div class="stat-card"><span>Unknown items</span><strong>{{ unknown_count }}</strong></div></section>
<section class="report-layout"><div class="report-card"><span class="eyebrow green-text">CATEGORY BREAKDOWN</span><h2>Items by material</h2>
{% set max_count = categories.values()|max if categories.values()|max > 0 else 1 %}
{% for category,count in categories.items() %}<div class="category-stat"><div><b>{{ category|title }}</b><span>{{ count }}</span></div><div class="progress"><span style="width:{{ (count / max_count * 100)|round(1) }}%"></span></div></div>{% endfor %}
</div><div class="eco-callout"><div class="eco-callout-icon">♻</div><span class="eyebrow">SMALL STEPS, BIG IMPACT</span><h2>Build better sorting habits.</h2><p>Correctly identifying materials is a useful first step towards responsible waste segregation and recycling.</p><a href="{{ url_for('classify') }}" class="btn btn-light">Classify an item →</a></div></section>
{% endblock %}'''

content["static/css/style.css"] = r''' 
:root{--green:#176b45;--green2:#2f9b68;--mint:#e8f5ed;--ink:#18352a;--muted:#73847b;--line:#e5eee8;--bg:#f7faf7;--shadow:0 16px 45px rgba(25,75,49,.08)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:'DM Sans',sans-serif}a{text-decoration:none;color:inherit}
.site-header{height:78px;background:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 max(calc((100vw - 1160px)/2),5%);border-bottom:1px solid #edf2ee;position:sticky;top:0;z-index:10}
.brand{display:flex;align-items:center;gap:10px;font:800 21px Manrope,sans-serif;letter-spacing:-.7px}.brand b{color:var(--green2)}.brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:13px;background:var(--mint);color:var(--green);font-size:23px}
.main-nav{display:flex;align-items:center;gap:8px}.main-nav a{padding:11px 18px;border-radius:30px;color:#63746b;font-weight:600;font-size:14px}.main-nav a:hover,.main-nav a.active{background:var(--mint);color:var(--green)}.menu-toggle{display:none;border:0;background:var(--mint);padding:9px 12px;border-radius:9px;font-size:20px}
.page-shell{max-width:1160px;margin:0 auto;padding:42px 24px 70px;min-height:calc(100vh - 145px)}
.home-hero{background:linear-gradient(120deg,#104e36,#1d8052);border-radius:30px;min-height:405px;padding:58px 7%;display:grid;grid-template-columns:1.1fr .9fr;align-items:center;overflow:hidden;position:relative;color:white}.hero-copy{position:relative;z-index:2}.eyebrow{font-size:10px;letter-spacing:2px;font-weight:800;color:#a8d9bd}.hero-copy h1{font:800 clamp(40px,5vw,62px)/1.08 Manrope,sans-serif;letter-spacing:-2.5px;margin:17px 0}.hero-copy h1 span{color:#b9edc9}.hero-copy p{color:#d2e9da;line-height:1.8;max-width:470px;font-size:15px;margin-bottom:26px}.btn{display:inline-flex;align-items:center;justify-content:center;gap:12px;padding:13px 21px;border:0;border-radius:12px;font:700 14px 'DM Sans';cursor:pointer;transition:.2s}.btn:hover{transform:translateY(-2px)}.btn-light{background:white;color:var(--green)}.btn-primary{background:var(--green);color:white}.btn-outline{border:1px solid #cbded1;background:white;color:var(--green)}.btn-danger{background:#fff0ef;color:#b94a43}.full{width:100%}.hero-note{margin-top:23px;color:#c6e2d0;font-size:12px}.hero-art{height:300px;display:grid;place-items:center;position:relative}.earth{width:190px;height:190px;border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at 35% 30%,#b9edbd,#4db47b 55%,#176b45);box-shadow:0 0 0 18px #ffffff0c,0 0 70px #b2efc044;font-size:86px;color:#eaffee;z-index:2}.orbit{position:absolute;border:1px solid #c4e9d055;border-radius:50%;width:280px;height:100px;transform:rotate(-25deg)}.orbit-two{width:320px;height:145px;transform:rotate(38deg)}.leaf{position:absolute;color:#b9edc9;font-size:43px}.leaf-a{top:34px;right:35px}.leaf-b{bottom:30px;left:38px;font-size:56px}.art-caption{position:absolute;bottom:0;color:#d8f1df;font-size:12px;letter-spacing:1px}
.section-heading{display:flex;justify-content:space-between;align-items:end;margin:54px 0 22px}.section-heading h2,.page-intro h1{font:800 30px Manrope;margin:8px 0;color:var(--ink);letter-spacing:-1px}.section-heading p,.page-intro p{color:var(--muted);margin:7px 0 0}.green-text{color:var(--green2)}.text-link{color:var(--green);font-size:13px;font-weight:700}
.category-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.category-card,.input-card,.stat-card,.report-card,.table-card,.form-panel,.camera-panel{background:white;border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow)}.category-card{padding:23px}.category-icon{width:49px;height:49px;border-radius:15px;display:grid;place-items:center;font-size:28px}.glass-icon{background:#e8f5ff;color:#4c99c5}.metal-icon{background:#f0efff;color:#7770c5}.paper-icon{background:#fff4e5;color:#ce9450}.plastic-icon{background:#e9f7ee;color:#319866}.category-card h3{margin:17px 0 5px;font:800 17px Manrope}.category-card p{margin:0;color:var(--muted);font-size:12px}.home-cta{margin-top:28px;padding:24px 28px;background:#edf7f0;border-radius:18px;display:flex;justify-content:space-between;align-items:center}.home-cta h2{font:800 20px Manrope;margin:8px 0}
.page-intro{margin:4px 0 30px}.page-intro h1{font-size:36px}.input-options{display:grid;grid-template-columns:repeat(3,1fr);gap:19px}.input-card{padding:27px;display:flex;flex-direction:column;min-height:340px}.input-card.featured{border-color:#a8d9ba}.option-icon{width:52px;height:52px;border-radius:16px;background:var(--mint);color:var(--green);font-size:28px;display:grid;place-items:center;margin-bottom:20px}.camera-icon{background:#edf4ff;color:#5d83c8}.video-icon{background:#fff1e9;color:#d58a58}.option-tag{font-size:10px;font-weight:800;letter-spacing:1.7px;color:var(--green2)}.input-card h2{font:800 21px Manrope;margin:9px 0}.input-card p{font-size:13px;color:var(--muted);line-height:1.7;margin:0 0 20px}.option-spacer{flex:1}.file-drop{border:1.5px dashed #b9d6c3;border-radius:15px;background:#f7fbf8;min-height:115px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:7px;margin:5px 0 15px;cursor:pointer;color:var(--green);font-size:12px}.file-drop input{max-width:95%;font-size:11px}.file-drop b{font-size:13px}.file-drop small{color:var(--muted);font-size:11px}.big-drop{min-height:180px}.notice{display:flex;gap:13px;align-items:flex-start;background:#edf7f0;border:1px solid #d9eddf;border-radius:14px;padding:16px 19px;margin-top:22px;color:var(--green)}.notice p{margin:0;color:#567363;font-size:12px;line-height:1.7}.flash-wrap{margin-bottom:18px}.flash{padding:13px 16px;border-radius:11px;font-size:13px;margin-bottom:8px;background:#fff3e3;color:#895b1e}
.camera-panel,.form-panel{max-width:700px;margin:0 auto;padding:24px}.camera-panel video{width:100%;max-height:430px;background:#17231c;border-radius:15px;object-fit:contain}.camera-actions{display:flex;gap:10px;margin:15px 0}.camera-panel form{margin-top:10px}.muted{color:var(--muted);font-size:12px}.center{text-align:center}.narrow{max-width:520px}.large-option-icon{font-size:42px;color:var(--green);text-align:center;margin:8px 0 20px}
.result-layout{display:grid;grid-template-columns:1.1fr .9fr;gap:24px;align-items:stretch}.result-image{background:#eaf2ec;border-radius:22px;overflow:hidden;min-height:380px;display:grid;place-items:center}.result-image img{width:100%;height:100%;max-height:520px;object-fit:contain}.result-card{background:white;border:1px solid var(--line);border-radius:22px;padding:32px;box-shadow:var(--shadow)}.prediction-name{font:800 40px Manrope;color:var(--green);margin:13px 0}.prediction-name.unknown{color:#b77928}.confidence-number{font:800 36px Manrope;margin:8px 0;color:var(--ink)}.confidence-number small{font-size:17px;color:var(--muted)}.progress,.mini-progress{height:9px;border-radius:20px;background:#edf2ee;overflow:hidden}.progress span,.mini-progress i{height:100%;display:block;border-radius:20px;background:linear-gradient(90deg,#58b77e,#176b45)}.result-explain{font-size:13px;color:var(--muted);line-height:1.7;margin:22px 0}.centered-link{display:block;text-align:center;margin-top:17px}
.split-intro{display:flex;justify-content:space-between;align-items:center}.table-card{overflow:hidden}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:760px}th,td{text-align:left;padding:16px 18px;border-bottom:1px solid var(--line);font-size:12px}th{background:#f8fbf8;color:#6c7e73;font-size:10px;letter-spacing:1px;text-transform:uppercase}tr:last-child td{border:0}.item-cell{display:flex;align-items:center;gap:10px;max-width:240px}.item-cell img{width:43px;height:43px;object-fit:cover;border-radius:9px;background:#edf3ee}.item-cell span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.class-pill{display:inline-block;background:#e9f6ed;color:#26784b;padding:6px 10px;border-radius:20px;font-size:11px;font-weight:700}.class-pill.unknown{background:#fff3e3;color:#a66b21}.table-confidence{min-width:100px}.mini-progress{height:5px;margin-top:7px}.mini-progress i{background:#53aa77}.empty-state{text-align:center;padding:65px 20px}.empty-state>div{font-size:48px;color:var(--green)}.empty-state h2{font:800 22px Manrope}.empty-state p{color:var(--muted);font-size:13px}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:28px}.stats-grid.three{grid-template-columns:repeat(3,1fr);margin:0 0 24px}.stat-card{padding:20px 23px}.stat-card span{display:block;color:var(--muted);font-size:12px}.stat-card strong{display:block;font:800 29px Manrope;margin-top:8px;color:var(--green)}
.report-layout{display:grid;grid-template-columns:1.1fr .9fr;gap:20px}.report-card{padding:27px}.report-card h2,.eco-callout h2{font:800 22px Manrope;margin:10px 0 25px}.category-stat{margin:19px 0}.category-stat>div:first-child{display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px}.category-stat>div:first-child span{color:var(--muted)}.eco-callout{border-radius:22px;padding:30px;background:linear-gradient(145deg,#176b45,#2c9562);color:white;display:flex;flex-direction:column;align-items:flex-start;justify-content:center}.eco-callout-icon{font-size:48px;margin-bottom:17px}.eco-callout .eyebrow{color:#c4ebd0}.eco-callout h2{font-size:27px;margin:12px 0}.eco-callout p{font-size:13px;line-height:1.8;color:#d7eee0;margin:0 0 23px}
.frame-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:17px;margin:22px 0}.frame-card{background:white;border:1px solid var(--line);border-radius:16px;overflow:hidden}.frame-card img{width:100%;height:170px;object-fit:cover;background:#e9f0eb}.frame-info{padding:13px;display:grid;gap:8px}.frame-info small{color:var(--muted)}
.footer{border-top:1px solid var(--line);background:white;padding:22px 5%;display:flex;justify-content:space-between;color:#839188;font-size:11px}.footer strong{color:var(--green)}
@media(max-width:800px){.site-header{height:68px}.menu-toggle{display:block}.main-nav{display:none;position:absolute;top:67px;left:0;right:0;background:white;padding:12px 5%;box-shadow:var(--shadow);flex-direction:column;align-items:stretch}.main-nav.open{display:flex}.main-nav a{padding:13px}.home-hero{grid-template-columns:1fr;padding:38px 7%}.hero-art{height:230px}.category-grid{grid-template-columns:repeat(2,1fr)}.stats-grid{grid-template-columns:repeat(2,1fr)}.input-options{grid-template-columns:1fr}.input-card{min-height:0}.result-layout,.report-layout{grid-template-columns:1fr}.result-image{min-height:260px}.frame-grid{grid-template-columns:repeat(2,1fr)}.split-intro{align-items:flex-start;gap:15px;flex-direction:column}.page-shell{padding:28px 16px 50px}}
@media(max-width:480px){.category-grid,.stats-grid.three,.frame-grid{grid-template-columns:1fr}.hero-copy h1{font-size:42px}.section-heading{align-items:flex-start;gap:10px;flex-direction:column}.page-intro h1{font-size:29px}.footer{gap:8px;flex-direction:column}.camera-actions{flex-direction:column}.result-card{padding:23px}.home-cta{align-items:flex-start;gap:15px;flex-direction:column}}
'''

# Save template and CSS files
for rel, data in content.items():
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(data).lstrip(), encoding="utf-8")

# Corrected app.py matching every template, retaining user's model and inference design
app_py = r'''import os
import json
import uuid
import base64
import sqlite3
import threading
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from ai_edge_litert.interpreter import Interpreter

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "waste_classifier.tflite"
CLASS_FILE = BASE_DIR / "class_names.json"
DATABASE = BASE_DIR / "database.db"
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

IMAGE_SIZE = (160, 160)
CONFIDENCE_THRESHOLD = 0.65
MARGIN_THRESHOLD = 0.15
ALLOWED_IMAGES = {"jpg", "jpeg", "png"}
ALLOWED_VIDEOS = {"mp4", "avi", "mov", "mkv"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ecosort-ai-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
if not CLASS_FILE.exists():
    raise FileNotFoundError(f"Class file not found: {CLASS_FILE}")

with open(CLASS_FILE, "r", encoding="utf-8") as f:
    CLASS_NAMES = json.load(f)

EXPECTED_CLASSES = ["glass", "metal", "paper", "plastic"]
if CLASS_NAMES != EXPECTED_CLASSES:
    raise ValueError(f"Expected class order {EXPECTED_CLASSES}, got {CLASS_NAMES}")

print("Loading EcoSort AI four-class model...")
interpreter = Interpreter(model_path=str(MODEL_PATH), num_threads=1)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
if int(output_details[0]["shape"][-1]) != 4:
    raise ValueError("The TFLite model must have exactly four outputs.")
inference_lock = threading.Lock()
print("Four-class TFLite model loaded successfully!")


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                waste_type TEXT,
                confidence REAL,
                source TEXT,
                timestamp TEXT
            )
        """)
        connection.commit()


init_db()


def save_history(filename, waste_type, confidence, source):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as connection:
        connection.execute("""
            INSERT INTO history (filename, waste_type, confidence, source, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (filename, waste_type, confidence, source, timestamp))
        connection.commit()


def softmax(values):
    values = values - np.max(values)
    exp_values = np.exp(values)
    return exp_values / np.sum(exp_values)


def predict_waste(image):
    image = image.convert("RGB").resize(IMAGE_SIZE)
    image_array = np.expand_dims(np.asarray(image, dtype=np.float32), axis=0)

    input_info = input_details[0]
    output_info = output_details[0]

    if input_info["dtype"] in (np.uint8, np.int8):
        scale, zero_point = input_info["quantization"]
        if scale > 0:
            image_array = np.round(image_array / scale + zero_point)
        limits = np.iinfo(input_info["dtype"])
        image_array = np.clip(image_array, limits.min, limits.max).astype(input_info["dtype"])
    else:
        image_array = image_array.astype(input_info["dtype"])

    with inference_lock:
        interpreter.set_tensor(input_info["index"], image_array)
        interpreter.invoke()
        predictions = interpreter.get_tensor(output_info["index"])[0]

    if output_info["dtype"] in (np.uint8, np.int8):
        scale, zero_point = output_info["quantization"]
        if scale > 0:
            predictions = (predictions.astype(np.float32) - zero_point) * scale

    predictions = predictions.astype(np.float32)
    if (np.any(predictions < 0) or np.any(predictions > 1)
            or not np.isclose(np.sum(predictions), 1.0, atol=0.02)):
        predictions = softmax(predictions)

    order = np.argsort(predictions)[::-1]
    best_index = int(order[0])
    confidence = float(predictions[best_index])
    second_confidence = float(predictions[order[1]])
    margin = confidence - second_confidence

    if confidence < CONFIDENCE_THRESHOLD or margin < MARGIN_THRESHOLD:
        return {"class": "Unknown Item", "confidence": round(confidence * 100, 2), "status": "unknown"}

    return {"class": CLASS_NAMES[best_index], "confidence": round(confidence * 100, 2), "status": "success"}


def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def unique_filename(filename):
    safe_name = secure_filename(filename)
    extension = Path(safe_name).suffix.lower()
    return f"{uuid.uuid4().hex}{extension}"


def save_upload(file):
    filename = unique_filename(file.filename)
    path = UPLOAD_FOLDER / filename
    file.save(path)
    return filename, path


def show_result(filename, prediction):
    return render_template(
        "result.html",
        predicted_class=prediction["class"],
        confidence=prediction["confidence"],
        image_url=url_for("uploaded_file", filename=filename)
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/classify", methods=["GET", "POST"])
def classify():
    if request.method == "GET":
        return render_template("classify.html")

    file = request.files.get("image")
    if not file or not file.filename:
        flash("Please select an image.")
        return redirect(url_for("classify"))
    if not allowed_file(file.filename, ALLOWED_IMAGES):
        flash("Please upload JPG, JPEG or PNG images.")
        return redirect(url_for("classify"))

    filename = None
    try:
        filename, path = save_upload(file)
        with Image.open(path) as source_image:
            image = source_image.convert("RGB")
        prediction = predict_waste(image)
        save_history(filename, prediction["class"], prediction["confidence"], "upload")
        return show_result(filename, prediction)
    except Exception:
        app.logger.exception("Image classification failed")
        if filename and (UPLOAD_FOLDER / filename).exists():
            (UPLOAD_FOLDER / filename).unlink()
        flash("Unable to analyse this image. Please try another file.")
        return redirect(url_for("classify"))


@app.route("/camera", methods=["GET", "POST"])
def camera():
    if request.method == "GET":
        return render_template("camera.html")

    camera_data = request.form.get("camera_image", "")
    if not camera_data:
        flash("Please capture an image first.")
        return redirect(url_for("camera"))

    filename = None
    try:
        if "," in camera_data:
            camera_data = camera_data.split(",", 1)[1]
        image_bytes = base64.b64decode(camera_data, validate=True)
        with Image.open(__import__("io").BytesIO(image_bytes)) as source_image:
            image = source_image.convert("RGB")
        filename = f"{uuid.uuid4().hex}.jpg"
        image.save(UPLOAD_FOLDER / filename, format="JPEG", quality=92)
        prediction = predict_waste(image)
        save_history(filename, prediction["class"], prediction["confidence"], "camera")
        return show_result(filename, prediction)
    except Exception:
        app.logger.exception("Camera classification failed")
        if filename and (UPLOAD_FOLDER / filename).exists():
            (UPLOAD_FOLDER / filename).unlink()
        flash("Unable to process camera image.")
        return redirect(url_for("camera"))


@app.route("/video", methods=["GET", "POST"])
def video():
    if request.method == "GET":
        return render_template("video.html")

    file = request.files.get("video")
    if not file or not file.filename:
        flash("Please select a video.")
        return redirect(url_for("video"))
    if not allowed_file(file.filename, ALLOWED_VIDEOS):
        flash("Unsupported video format.")
        return redirect(url_for("video"))

    video_filename, video_path = save_upload(file)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        flash("Unable to open the video.")
        return redirect(url_for("video"))

    analysed_frames = 0
    recognised_count = 0
    unknown_count = 0
    results = []
    frame_number = 0

    try:
        while len(results) < 30:
            success, frame = capture.read()
            if not success:
                break
            frame_number += 1
            if frame_number % 15 != 0:
                continue

            analysed_frames += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            prediction = predict_waste(image)

            if prediction["status"] == "success":
                recognised_count += 1
            else:
                unknown_count += 1

            image_filename = f"{uuid.uuid4().hex}.jpg"
            image.save(UPLOAD_FOLDER / image_filename, format="JPEG", quality=90)
            save_history(image_filename, prediction["class"], prediction["confidence"], "video")

            results.append({
                "image_url": url_for("uploaded_file", filename=image_filename),
                "prediction": prediction["class"],
                "confidence": prediction["confidence"],
                "frame_number": frame_number
            })
    finally:
        capture.release()

    if not results:
        flash("No frames were sampled. Try a longer video.")
        return redirect(url_for("video"))

    return render_template(
        "video_result.html",
        total_frames=analysed_frames,
        recognised_count=recognised_count,
        unknown_count=unknown_count,
        results=results,
        items=results
    )


@app.route("/history")
def history():
    with get_db() as connection:
        records = connection.execute("SELECT * FROM history ORDER BY id DESC").fetchall()
    return render_template("history.html", records=records)


@app.route("/reports")
def reports():
    with get_db() as connection:
        records = connection.execute("""
            SELECT waste_type, COUNT(*) AS count
            FROM history GROUP BY waste_type
        """).fetchall()
        total = connection.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    categories = {name: 0 for name in EXPECTED_CLASSES}
    unknown_count = 0
    for record in records:
        category = record["waste_type"]
        if category in categories:
            categories[category] = record["count"]
        else:
            unknown_count += record["count"]

    return render_template(
        "reports.html",
        total=total,
        categories=categories,
        unknown_count=unknown_count
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/clear-history", methods=["POST"])
def clear_history():
    with get_db() as connection:
        connection.execute("DELETE FROM history")
        connection.commit()
    flash("Classification history cleared.")
    return redirect(url_for("history"))


@app.route("/health")
def health():
    return {"status": "healthy", "model": "loaded", "classes": CLASS_NAMES}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
'''
(root / "app.py").write_text(app_py, encoding="utf-8")
(root / "class_names.json").write_text('["glass", "metal", "paper", "plastic"]\n', encoding="utf-8")
(root / "requirements.txt").write_text(
    "Flask>=3.0\nnumpy<2.3\nPillow>=10.0\nai-edge-litert>=1.0.1\nopencv-python-headless>=4.9\n",
    encoding="utf-8"
)
(root / "SETUP.txt").write_text(
    "ECOSORT AI CORRECTED FILES\n\n"
    "Copy app.py, class_names.json and requirements.txt into your project root.\n"
    "Copy templates/ and static/ folders into the same project root.\n"
    "Keep your existing waste_classifier.tflite and database.db files.\n\n"
    "Install: python -m pip install -r requirements.txt\n"
    "Run: python app.py\n"
    "Open: http://127.0.0.1:5000\n\n"
    "Important: class_names.json order must match the model's training output order.\n"
    "This code expects a 4-output model and RGB pixel input 0-255. It assumes the TFLite\n"
    "model includes any required input rescaling layer. Unknown is a confidence/margin\n"
    "rejection heuristic and cannot guarantee rejection of every unsupported object.\n",
    encoding="utf-8"
)

zip_path = root.parent / "EcoSort_AI_Corrected_Full_Code.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in root.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to(root.parent))

print(f"Created {zip_path}")
print("Files included:")
for p in sorted(root.rglob("*")):
    if p.is_file():
        print(p.relative_to(root))

        
from flask import Flask

app = Flask(__name__)