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
  const filtersEl = document.getElementById('filters');
  const calEl = document.getElementById('calendar');

  // 1) Load association-color map, then events
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

      // Build filters
      const assocs = Array.from(new Set(eventsData.map(e => e.extendedProps.association)));
      filtersEl.innerHTML = '';
      assocs.forEach(assoc => {
        const id = `f-${assoc}`;
        const cb = document.createElement('input');
        cb.type = 'checkbox'; cb.id = id; cb.value = assoc; cb.checked = true;

        const lbl = document.createElement('label');
        lbl.htmlFor = id;
        lbl.append(cb, ' ', assoc);

        filtersEl.append(lbl);
        cb.addEventListener('change', () => calendar.refetchEvents());
      });

      // 3) FullCalendar
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

          // Formatters
          const fmtDate = d => d?.toLocaleDateString(LOCALE, { year:'numeric', month:'long', day:'numeric' });
          const fmtDateTime = d => d?.toLocaleString(LOCALE, {
            year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit'
          });

          // Fill modal
          document.getElementById('modalTitle').textContent = e.title;

          const dateStr = e.allDay
            ? fmtDate(e.start)
            : `${fmtDateTime(e.start)}${e.end ? ` → ${fmtDateTime(e.end)}` : ''}`;
          document.getElementById('modalDate').textContent = dateStr;

          document.getElementById('modalLocation').textContent = e.extendedProps.location || '—';
          document.getElementById('modalDesc').textContent = e.extendedProps.description || '';

          const img = document.getElementById('modalImage');
          if (e.extendedProps.image) { img.src = e.extendedProps.image; img.style.display = 'block'; }
          else { img.style.display = 'none'; }

          const link = document.getElementById('modalLink');
          const href = e.extendedProps.registrationLink || e.url;
          if (href) { link.href = href; link.style.display = 'inline-block'; }
          else { link.style.display = 'none'; }

          // Show modal (single, clean block)
          const backdrop = document.getElementById('detailBackdrop');
          const modal    = document.getElementById('detailModal');
          const content  = document.getElementById('detailContent');

          backdrop.style.display = 'block';
          modal.style.display = 'flex';
          document.body.classList.add('modal-open');
          if (content) content.scrollTop = 0;
          document.addEventListener('keydown', escHandler);
        }
      });

      calendar.render();
    })
    .catch(err => console.error('Loading error:', err));
});

