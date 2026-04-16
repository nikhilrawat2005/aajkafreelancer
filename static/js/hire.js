// static/js/hire.js

document.addEventListener('DOMContentLoaded', function () {

  const hireBtn = document.getElementById('hire-btn');
  if (!hireBtn) return;

  const conversationId = hireBtn.dataset.conversationId;

  function setButtonState({ text, classesToAdd = [], disabled = false }) {
    hireBtn.textContent = text;
    hireBtn.disabled = disabled;
    hireBtn.classList.remove('hire-default', 'hire-pending', 'hire-accepted', 'hire-rejected');
    classesToAdd.forEach(c => hireBtn.classList.add(c));
  }

  function setupRequestClick() {
    hireBtn.onclick = async () => {
      hireBtn.disabled = true;
      try {
        const res = await fetch(`/chat/hire/request/${conversationId}`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': window.CSRF_TOKEN
          }
        });

        const data = await res.json();

        if (data.success) {
          setButtonState({
            text: 'Request Sent',
            classesToAdd: ['hire-pending'],
            disabled: true
          });
        } else {
          alert(data.error || 'Could not send hire request.');
          hireBtn.disabled = false;
        }
      } catch (err) {
        console.log(err);
        hireBtn.disabled = false;
      }
    };
  }

  function setupRecordClick(hire) {
    const modal = document.getElementById('hire-modal');
    const form = document.getElementById('hire-record-form');
    const cancelBtn = document.getElementById('hire-modal-cancel');
    
    if (!modal || !form || !cancelBtn) return;

    hireBtn.onclick = () => {
      modal.style.display = 'flex';
      // Pre-fill existing data if any
      document.getElementById('hire-title').value = hire.work_title || '';
      document.getElementById('hire-desc').value = hire.work_description || '';
    };

    cancelBtn.onclick = () => {
      modal.style.display = 'none';
    };

    form.onsubmit = async (e) => {
      e.preventDefault();
      if (!hire || !hire.request_id) return;

      const title = document.getElementById('hire-title').value.trim();
      const description = document.getElementById('hire-desc').value.trim();
      const startDate = document.getElementById('hire-start').value;
      const endDate = document.getElementById('hire-end').value;

      const submitBtn = document.getElementById('hire-modal-submit');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Saving...';

      try {
        const res = await fetch(`/chat/hire/record/${hire.request_id}`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': window.CSRF_TOKEN,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            title: title || '',
            description: description || '',
            start_date: startDate || null,
            end_date: endDate || null
          })
        });

        const data = await res.json();

        if (data.success) {
          modal.style.display = 'none';
          setButtonState({
            text: 'Work Recorded',
            classesToAdd: ['hire-accepted'],
            disabled: true
          });
          // Optional: send a message in chat that work is recorded
        } else {
          alert(data.error || 'Could not save work record.');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Save Work Details';
        }
      } catch (err) {
        console.error(err);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Work Details';
      }
    };
  }

  async function loadHireStatus() {
    try {
      const res = await fetch(`/chat/hire/status/${conversationId}`);
      if (!res.ok) {
        setupRequestClick();
        return;
      }

      const data = await res.json();

      // If a completed work record exists, always show that state
      if (data && data.record_created) {
        setButtonState({
          text: 'Work Recorded',
          classesToAdd: ['hire-accepted'],
          disabled: true
        });
        if (data.work_title) {
          hireBtn.title = `Recorded work: ${data.work_title}`;
        }
        return;
      }

      if (!data || !data.status) {
        setButtonState({
          text: 'Hire Worker',
          classesToAdd: ['hire-default'],
          disabled: false
        });
        setupRequestClick();
        return;
      }

      if (data.status === 'pending') {
        setButtonState({
          text: data.is_requester ? 'Request Pending' : 'Client requested hire',
          classesToAdd: ['hire-pending'],
          disabled: true
        });
        hireBtn.title = data.is_requester
          ? 'Your hire request is waiting for the worker.'
          : 'You have a pending hire request from this client.';
        return;
      }

      if (data.status === 'accepted') {
        if (data.is_requester && !data.record_created) {
          setButtonState({
            text: 'Add Work Details',
            classesToAdd: ['hire-accepted'],
            disabled: false
          });
          hireBtn.title = 'The worker accepted. Click to save work details.';
          setupRecordClick(data);
        } else {
          setButtonState({
            text: data.record_created ? 'Work Recorded' : 'Hire Accepted',
            classesToAdd: ['hire-accepted'],
            disabled: true
          });
        }
        return;
      }

      if (data.status === 'rejected') {
        setButtonState({
          text: 'Request Rejected',
          classesToAdd: ['hire-rejected'],
          disabled: true
        });
        hireBtn.title = 'This hire request was rejected.';
        return;
      }

      setButtonState({
        text: 'Hire Worker',
        classesToAdd: ['hire-default'],
        disabled: false
      });
      setupRequestClick();
    } catch (err) {
      console.log(err);
      setButtonState({
        text: 'Hire Worker',
        classesToAdd: ['hire-default'],
        disabled: false
      });
      setupRequestClick();
    }
  }

  loadHireStatus();

});
