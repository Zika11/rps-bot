import { useEffect } from 'react'

function TelegramLoginButton({ botName, onAuth }) {
  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.setAttribute('data-telegram-login', botName)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    document.getElementById('telegram-login-container').appendChild(script)

    window.onTelegramAuth = (user) => {
      onAuth(user)
    }

    return () => {
      document.getElementById('telegram-login-container').innerHTML = ''
      delete window.onTelegramAuth
    }
  }, [botName, onAuth])

  return <div id="telegram-login-container"></div>
}

export default TelegramLoginButton
