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

function boutonCurseurEntré(bouton){
  bouton.style.borderColor = "#ff6600ff";
}

function boutonCurseurSortis(bouton){
  bouton.style.borderColor = "#0000";
}

function boutonClique(bouton){
  console.log("clique");
  if (bouton.getAttribute("data-checked") === "true"){
    bouton.setAttribute("data-checked", false);
    bouton.style.opacity = "0.5";
  }else {
    bouton.setAttribute("data-checked", true);
    bouton.style.opacity = "1";
  }

  calendar.refetchEvents();
}

// Prend un string représentant une couleur et renvoie une liste sur le format RGB 0-255
function lireCouleur(couleur){
  RGB = [0,0,0]

  // Extraire les valeurs RGB en format #RRGGBB ou rgb(r, g, b)
  if (couleur[0] === "#"){
    RGB[0] = parseInt(couleur.substring(1,3),16);
    RGB[1] = parseInt(couleur.substring(3,5),16);
    RGB[2] = parseInt(couleur.substring(5,7),16);
  } else {
    numéros = couleur.split("(")[1].split(")")[0].replace(" ","").split(","); // "rgb(A, B, C)"" → [A,B,C]
    RGB[0] = parseFloat(numéros[0])*255;
    RGB[1] = parseFloat(numéros[1])*255;
    RGB[2] = parseFloat(numéros[2])*255;
  }

  return RGB;
}

// Prend une liste sur le format RGB 0-255 et renvoie un string sur le format #RRGGBB
function RGB2String(RGB){
  rgb = RGB;

  rgb[0] = Math.round(rgb[0]).toString(16);
  rgb[1] = Math.round(rgb[1]).toString(16);
  rgb[2] = Math.round(rgb[2]).toString(16);

  rgb[0] = ( rgb[0].length == 1 )? "0"+rgb[0] : rgb[0];
  rgb[1] = ( rgb[1].length == 1 )? "0"+rgb[1] : rgb[1];
  rgb[2] = ( rgb[2].length == 1 )? "0"+rgb[2] : rgb[2];

  return "#"+rgb[0]+rgb[1]+rgb[2];
}

// Modifie la luminosité d'une couleur
function luminositéCouleur(couleur, lumPourcent){
  RGB = lireCouleur(couleur);

  // Manipulation
  RGB[0] = RGB[0] * (100 + lumPourcent) / 100;
  RGB[1] = RGB[1] * (100 + lumPourcent) / 100;
  RGB[2] = RGB[2] * (100 + lumPourcent) / 100;

  // Limitation en-dessous de 255
  RGB[0] = RGB[0]<255? RGB[0] : 255;
  RGB[1] = RGB[1]<255? RGB[1] : 255;
  RGB[2] = RGB[2]<255? RGB[2] : 255;

  return RGB2String(RGB);
}

document.addEventListener('DOMContentLoaded', () => {
  // Always start closed (covers reloads + bfcache restores)
  closeModal();
  window.addEventListener('pageshow', () => closeModal(), { once: true });

  const filtersEl = document.getElementById('filtres');
  const calEl = document.getElementById('calendrier');

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
        const cb = document.createElement('div');
        cb.id = id;
        cb.setAttribute("data-checked",true);
        cb.classList.add("filtres-bouton");
        cb.innerText = assoc;
        cb.style.background = assocColors[assoc];
        cb.style.boxShadow = "3px 4px 0 "+luminositéCouleur(assocColors[assoc],-40);

        filtersEl.append(cb);

        cb.addEventListener('change', () => calendar.refetchEvents());
        cb.addEventListener('mouseenter', () => boutonCurseurEntré(cb));
        cb.addEventListener('mouseleave', () => boutonCurseurSortis(cb));
        cb.addEventListener('click', () => boutonClique(cb));
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
            const chosen = Array.from(filtersEl.querySelectorAll("[data-checked='true']")).map(cb => cb.innerText);
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
          const link = document.getElementById('lienInscription');
          const href = e.extendedProps.registrationLink || e.url;
          if (href) { link.href = href; link.style.display = 'inline-block'; }
          else { link.style.display = 'none'; }

          // couleurs
          const arrièrePlan = document.getElementById('detailModal');
          const coulLumineux = luminositéCouleur(assocColors[e.extendedProps.association],10);
          const coulSombre = luminositéCouleur(assocColors[e.extendedProps.association],-10);
          arrièrePlan.style.background = "repeating-linear-gradient(-45deg, "+coulLumineux+" 0px,"+coulLumineux+" 40px,"+coulSombre+" 40px,"+coulSombre+" 80px)";

          const header = document.getElementById('modal_header');
          header.style.backgroundColor = luminositéCouleur(assocColors[e.extendedProps.association], 40);
          
          const footer = document.getElementById('modal_footer');
          footer.style.backgroundColor = luminositéCouleur(assocColors[e.extendedProps.association], 40);

          // Show modal
          document.getElementById('detailBackdrop').style.display = 'flex';
          arrièrePlan.style.display = 'flex';
          document.body.classList.add('modal-open');
          document.getElementById('detailContent').scrollTop = 0;
          document.addEventListener('keydown', escHandler);
        }
      });

      calendar.render();
    })
    .catch(err => console.error('Loading error:', err));
});

