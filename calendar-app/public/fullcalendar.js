function closeModal() {
  document.getElementById('detailModal').style.display = 'none';
  document.getElementById('detailBackdrop').style.display = 'none';
}

let eventsData = [];
let assocColors = {};
const LOCALE = 'fr-CA'; // french (Canada). Use 'fr-FR' if you prefer.

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
      // inject colors (same as before)
      eventsData = data.map(e => {
        const c = assocColors[e.extendedProps.association] || '#3788d8';
        return { ...e, backgroundColor: c, borderColor: c };
      });

      // build filters dynamically
      const assocs = Array.from(new Set(eventsData.map(e => e.extendedProps.association)));
      filtersEl.innerHTML = '';
      assocs.forEach(assoc => {
        const id = `f-${assoc}`;
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.id = id;
        cb.value = assoc;
        cb.checked = true;

        const lbl = document.createElement('label');
        lbl.htmlFor = id;
        lbl.append(cb, ' ', assoc);

        filtersEl.append(lbl);
        cb.addEventListener('change', () => calendar.refetchEvents());
      });

      // 3) Initialize FullCalendar (unchanged logic; just localized UI)
      window.calendar = new FullCalendar.Calendar(calEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },

        // --- Localization additions ---
        locale: 'fr',          // requires locales build for full month/day names
        firstDay: 1,           // Monday start (common in FR)
        buttonText: {          // fallback labels (work even without locales-all)
          today: 'Aujourd’hui',
          month: 'Mois',
          week: 'Semaine',
          day: 'Jour',
          list: 'Liste'
        },
        weekText: 'Sem.',
        allDayText: 'Toute la journée',
        noEventsText: 'Aucun événement à afficher',
        // ------------------------------

        eventSources: [{
          events: (info, success) => {
            const chosen = Array.from(filtersEl.querySelectorAll('input:checked'))
              .map(cb => cb.value);
            const filtered = eventsData.filter(e =>
              chosen.includes(e.extendedProps.association)
            );
            success(filtered);
          }
        }],
        eventClick: info => {
          const e = info.event;
          document.getElementById('modalTitle').innerText = e.title;

          // French date formatting (same logic, just localized output)
          const fmtDate = (d) => d?.toLocaleDateString(LOCALE, {
            year: 'numeric', month: 'long', day: 'numeric'
          });
          const fmtDateTime = (d) => d?.toLocaleString(LOCALE, {
            year: 'numeric', month: 'long', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
          });

          document.getElementById('modalDate').innerText = e.allDay
            ? fmtDate(e.start)
            : `${fmtDateTime(e.start)} → ${e.end ? fmtDateTime(e.end) : ''}`;

          document.getElementById('modalLocation').innerText = e.extendedProps.location || '—';
          document.getElementById('modalDesc').innerText = e.extendedProps.description || '';

          const img = document.getElementById('modalImage');
          if (e.extendedProps.image) {
            img.src = e.extendedProps.image;
            img.style.display = 'block';
          } else {
            img.style.display = 'none';
          }

          const link = document.getElementById('modalLink');
          const href = e.extendedProps.registrationLink || e.url;
          if (href) {
            link.href = href;
            link.style.display = 'inline-block';
          } else {
            link.style.display = 'none';
          }

          document.getElementById('detailBackdrop').style.display = 'block';
          document.getElementById('detailModal').style.display = 'block';
        }
      });

      calendar.render();
    })
    .catch(err => console.error('Loading error:', err));
});

