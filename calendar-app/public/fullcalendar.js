function closeModal() {
  document.getElementById('detailModal').style.display = 'none';
  document.getElementById('detailBackdrop').style.display = 'none';
  document.body.classList.remove('modal-open');
  document.removeEventListener('keydown', escHandler);
}
function escHandler(e){ if (e.key === 'Escape') closeModal(); }

let eventsData = [];
let assocColors = {};
const LOCALE = 'fr-CA';

document.addEventListener('DOMContentLoaded', () => {
  // Always start closed (covers reloads + bfcache restores)
  closeModal();
  window.addEventListener('pageshow', () => closeModal(), { once: true });

  const filtersEl = document.getElementById('filters');
  const calEl = document.getElementById('calendar');

  // Load colors then events
  fetch('/assoc-colors.json', { cache: 'no-store' })
    .then(r => r.json())
    .then(colors => {
      assocColors = colors;
      return fetch('/events.json', { cache: 'no-store' }).then(r => r.json());
    })
    .then(data => {
      eventsData = data.map(e => {
        const c = assocColors[e.extendedProps.association] || '#3788d8';
        return { ...e, backgroundColor: c, borderColor: c };
      });

      // Filters
      const assocs = Array.from(new Set(eventsData.map(e => e.extendedProps.association)));
      filtersEl.innerHTML = '';
      assocs.forEach(assoc => {
        const id = `f-${assoc}`;
        const cb = document.createElement('input');
        cb.type = 'checkbox'; cb.id = id; cb.value = assoc; cb.checked = true;

        const lbl = document.createElement('label');
        lbl.htmlFor = id; lbl.append(cb, ' ', assoc);
        filtersEl.append(lbl);

        cb.addEventListener('change', () => calendar.refetchEvents());
      });

      // Calendar
      window.calendar = new FullCalendar.Calendar(calEl, {
        initialView: 'dayGridMonth',
        headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' },
        locale: 'fr',
        firstDay: 1,
        buttonText: { today:'Aujourd’hui', month:'Mois', week:'Semaine', day:'Jour', list:'Liste' },
        weekText: 'Sem.',
        allDayText: 'Toute la journée',
        noEventsText: 'Aucun événement à afficher',

        eventSources: [{
          events: (info, success) => {
            const chosen = Array.from(filtersEl.querySelectorAll('input:checked')).map(cb => cb.value);
            success(eventsData.filter(e => chosen.includes(e.extendedProps.association)));
          }
        }],

        eventClick: info => {
          const e = info.event;

          const fmtDate = d => d?.toLocaleDateString(LOCALE, { year:'numeric', month:'long', day:'numeric' });
          const fmtTime = d => d?.toLocaleTimeString(LOCALE, { hour:'2-digit', minute:'2-digit' });
          const sameDay = e.end && e.start && e.start.toDateString() === e.end.toDateString();

          // Title
          document.getElementById('modalTitle').textContent = e.title;

          // Date row
          const dateStr = e.allDay
            ? fmtDate(e.start)
            : (e.end && !sameDay ? `${fmtDate(e.start)} → ${fmtDate(e.end)}` : fmtDate(e.start));
          document.getElementById('modalDate').textContent = dateStr;

          // Time row
          const timeStr = e.allDay
            ? 'Toute la journée'
            : `${fmtTime(e.start)}${e.end ? ` → ${fmtTime(e.end)}` : ''}`;
          document.getElementById('modalTime').textContent = timeStr;

          // Location + Description
          document.getElementById('modalLocation').textContent = e.extendedProps.location || '—';
          document.getElementById('modalDesc').textContent = e.extendedProps.description || '';

          // Poster
          const img = document.getElementById('modalImage');
          if (e.extendedProps.image) { img.src = e.extendedProps.image; img.style.display = 'block'; }
          else { img.style.display = 'none'; }

          // Link
          const link = document.getElementById('modalLink');
          const href = e.extendedProps.registrationLink || e.url;
          if (href) { link.href = href; link.style.display = 'inline-block'; }
          else { link.style.display = 'none'; }

          // Show modal
          document.getElementById('detailBackdrop').style.display = 'block';
          document.getElementById('detailModal').style.display = 'flex';
          document.body.classList.add('modal-open');
          document.getElementById('detailContent').scrollTop = 0;
          document.addEventListener('keydown', escHandler);
        }
      });

      calendar.render();
    })
    .catch(err => console.error('Loading error:', err));
});

