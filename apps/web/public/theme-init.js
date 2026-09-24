;(function () {
  var stored = null
  var dark = false
  // Separate guards: blocked storage must not hide the system colour-scheme preference.
  try {
    stored = window.localStorage.getItem('ddq-theme')
  } catch (error) {
    // storage unavailable: treat as "no stored preference"
  }
  try {
    dark = window.matchMedia('(prefers-color-scheme: dark)').matches
  } catch (error) {
    // matchMedia unavailable: keep the light default
  }
  var theme = stored === 'dark' || (stored !== 'light' && dark) ? 'dark' : 'light'
  document.documentElement.dataset.theme = theme
})()
