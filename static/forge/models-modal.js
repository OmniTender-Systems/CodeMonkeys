window.switchModelsTab = function(tabName, btn) {
  document.querySelectorAll('#mmodal-nav .mmodal-tab').forEach(b => {
    b.className = 'mmodal-tab px-3 py-1.5 rounded font-medium text-slate-400 hover:text-slate-200 border border-transparent';
  });
  if (btn) {
    btn.className = 'mmodal-tab px-3 py-1.5 rounded font-medium bg-yellow-900/30 text-yellow-300 border border-yellow-700/50';
  }
  document.querySelectorAll('.mview-tab').forEach(el => el.classList.add('hidden'));
  const target = document.getElementById('mview-' + tabName);
  if (target) target.classList.remove('hidden');
};
