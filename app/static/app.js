const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const statusSpan = document.getElementById('status');
const transcriptText = document.getElementById('transcriptText');
const responseText = document.getElementById('responseText');
const responseAudio = document.getElementById('responseAudio');
const metaSession = document.getElementById('metaSession');
const metaConfidence = document.getElementById('metaConfidence');
const metaEscalated = document.getElementById('metaEscalated');

const textQuery = document.getElementById('textQuery');
const sendText = document.getElementById('sendText');
const textResponse = document.getElementById('textResponse');

let mediaRecorder;
let audioChunks = [];

async function initMedia() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.onstart = () => {
      audioChunks = [];
      statusSpan.textContent = 'Recording...';
      recordBtn.disabled = true;
      stopBtn.disabled = false;
    };

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      statusSpan.textContent = 'Processing...';
      recordBtn.disabled = false;
      stopBtn.disabled = true;

      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      transcriptText.textContent = 'Sending audio...';

      // Build multipart form
      const form = new FormData();
      form.append('customer_id', 'web_demo');
      form.append('audio_file', blob, 'question.webm');

      try {
        const res = await fetch('/api/v1/agent/voice-query', {
          method: 'POST',
          body: form
        });

        if (!res.ok) {
          const txt = await res.text();
          responseText.textContent = `Error: ${res.status} ${txt}`;
          statusSpan.textContent = 'Idle';
          return;
        }

        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('audio')) {
          const sessionId = res.headers.get('X-Session-ID');
          const confidence = res.headers.get('X-Confidence-Score');
          const escalated = res.headers.get('X-Escalated');
          metaSession.textContent = `Session: ${sessionId || '—'}`;
          metaConfidence.textContent = `Confidence: ${confidence || '—'}`;
          metaEscalated.textContent = `Escalated: ${escalated || '—'}`;

          const arrayBuffer = await res.arrayBuffer();
          const audioBlob = new Blob([arrayBuffer], { type: 'audio/wav' });
          responseAudio.src = URL.createObjectURL(audioBlob);
          responseAudio.play();

          // Optionally fetch transcript header X-Transcript if available
          const transcript = res.headers.get('X-Transcript');
          transcriptText.textContent = transcript || '—';
          responseText.textContent = 'Played response audio.';
          statusSpan.textContent = 'Idle';
        } else {
          // JSON fallback
          const data = await res.json();
          transcriptText.textContent = data.transcript || '—';
          responseText.textContent = data.response || '—';
          metaSession.textContent = `Session: ${data.session_id || '—'}`;
          metaConfidence.textContent = `Confidence: ${data.confidence_score || '—'}`;
          metaEscalated.textContent = `Escalated: ${data.escalated}`;
          statusSpan.textContent = 'Idle';

          // Use browser TTS as fallback
          if ('speechSynthesis' in window && data.response) {
            const utter = new SpeechSynthesisUtterance(data.response);
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utter);
          }
        }

      } catch (e) {
        responseText.textContent = `Error: ${e}`;
        statusSpan.textContent = 'Idle';
      }
    };

  } catch (e) {
    statusSpan.textContent = 'Microphone access denied';
    recordBtn.disabled = true;
    console.error('getUserMedia failed', e);
  }
}

recordBtn.addEventListener('click', async () => {
  if (!mediaRecorder) await initMedia();
  mediaRecorder.start();
});

stopBtn.addEventListener('click', () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
});

// Text query flow: call text endpoint and use Web Speech API for TTS fallback
sendText.addEventListener('click', async () => {
  const q = textQuery.value.trim();
  if (!q) return;
  textResponse.textContent = 'Sending...';

  try {
    const res = await fetch('/api/v1/agent/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: 'web_demo', query: q })
    });

    if (!res.ok) {
      textResponse.textContent = `Error: ${res.status}`;
      return;
    }

    const data = await res.json();
    textResponse.textContent = data.response;

    // Speak using browser TTS as fallback
    if ('speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(data.response);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }

  } catch (e) {
    textResponse.textContent = `Error: ${e}`;
  }
});

// Initialize if possible
initMedia();
