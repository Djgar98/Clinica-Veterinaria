// Global helpers
(function(){
  // Highlight active nav link
  try {
    const links = document.querySelectorAll('.navbar-nav .nav-link, .list-group .list-group-item');
    const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    links.forEach(a => {
      const href = a.getAttribute('href');
      if (!href || href === '#') return;
      const linkPath = href.replace(/\/+$/, '') || '/';
      if (linkPath === currentPath) {
        a.classList.add('active');
        a.setAttribute('aria-current', 'page');
      }
    });
  } catch (e) {}

  // Bootstrap validation
  const forms = document.querySelectorAll('.needs-validation');
  Array.from(forms).forEach((form) => {
    form.addEventListener('submit', function (event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    }, false);
  });

  // Bootstrap tooltips
  try {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach((tooltipTriggerEl) => {
      new bootstrap.Tooltip(tooltipTriggerEl);
    });
  } catch (e) {}
})();

// Debounce utility
function debounce(fn, wait){ let t; return function(...args){ clearTimeout(t); t = setTimeout(()=>fn.apply(this,args), wait); }; }

// Global search autocomplete
(function(){
  const input = document.getElementById('global-search');
  const box = document.getElementById('search-suggestions');
  if (!input || !box) return;
  let activeIndex = -1;
  const setExpanded = (isOpen)=> input.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  const clearActive = ()=>{
    const items = box.querySelectorAll('[role="option"]');
    items.forEach(i=>{ i.classList.remove('active'); i.setAttribute('aria-selected','false'); });
    activeIndex = -1;
    input.removeAttribute('aria-activedescendant');
  };
  const setActive = (index)=>{
    const items = box.querySelectorAll('[role="option"]');
    if (!items.length) return;
    activeIndex = Math.max(0, Math.min(index, items.length - 1));
    items.forEach(i=>{ i.classList.remove('active'); i.setAttribute('aria-selected','false'); });
    const active = items[activeIndex];
    active.classList.add('active');
    active.setAttribute('aria-selected','true');
    input.setAttribute('aria-activedescendant', active.id);
    active.scrollIntoView({ block: 'nearest' });
  };
  input.addEventListener('keydown', (e)=>{
    const items = box.querySelectorAll('[role="option"]');
    if (e.key === 'ArrowDown' && items.length) { e.preventDefault(); setActive(activeIndex + 1); }
    if (e.key === 'ArrowUp' && items.length) { e.preventDefault(); setActive(activeIndex - 1); }
    if (e.key === 'Enter' && activeIndex >= 0 && items[activeIndex]) { e.preventDefault(); items[activeIndex].click(); }
    if (e.key === 'Escape') { box.style.display='none'; setExpanded(false); clearActive(); }
  });
  const render = (data)=>{
    box.innerHTML = '';
    clearActive();
    if (!data || !data.results || !data.results.length){
      box.style.display='none';
      setExpanded(false);
      return;
    }
    data.results.forEach((r, idx)=>{
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'list-group-item list-group-item-action';
      item.setAttribute('role','option');
      item.setAttribute('tabindex','-1');
      item.setAttribute('aria-selected','false');
      item.id = 'search-option-' + idx;
      item.innerHTML = `<div><strong>${r.nombre}</strong> <small class="text-muted">(${r.precio})</small></div>`;
      item.addEventListener('click', ()=>{
        window.location.href = '/inventario/?q=' + encodeURIComponent(r.nombre);
      });
      box.appendChild(item);
    });
    box.style.display = 'block';
    setExpanded(true);
  };
  const fetchSuggestions = debounce(function(){
    const q = input.value.trim();
    if (!q){
      box.style.display='none';
      setExpanded(false);
      clearActive();
      return;
    }
    fetch('/inventario/api/products/?q=' + encodeURIComponent(q))
      .then(r=>r.json())
      .then(render)
      .catch(()=>{ box.style.display='none'; });
  }, 250);
  input.addEventListener('input', fetchSuggestions);
  document.addEventListener('click', (e)=>{
    if (!box.contains(e.target) && e.target !== input){
      box.style.display='none';
      setExpanded(false);
      clearActive();
    }
  });
})();
