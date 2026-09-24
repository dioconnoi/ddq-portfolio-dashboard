;(function () {
  var theme = 'light'
  try {
    var stored = window.localStorage.getItem('ddq-theme')
    var dark = window.matchMedia('(prefers-color-scheme: dark)').matches
    if (stored === 'dark' || (stored !== 'light' && dark)) theme = 'dark'
  } catch (error) {
    // storage or matchMedia unavailable: keep the light default
  }
  document.documentElement.dataset.theme = theme
})()
