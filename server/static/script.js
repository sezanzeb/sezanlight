'use strict'

let r = 0
let g = 0
let b = 0
// this variable is set on all the clients and on the server as well.
// the range of values the raspberry accepts for each color channel
let config = { clr_range: 255 }
let hide_status_timeout = null

// color and config tabs based on target attribute
const tabs = []
const buttons = []
function hide_all() {
    for (const tab of tabs) {
        tab.className = tab.className.replace('active', '').replace(' ', ' ').trim()
    }
    for (const button of buttons) {
        button.className = button.className.replace('active', '').replace(' ', ' ').trim()
    }
}
function show(target, button) {
    target.className = (target.className.trim() + ' active').trim()
    button.className = (button.className.trim() + ' active').trim()
}
for (const button of document.querySelectorAll('*[target]')) {
    const target = document.getElementById(button.attributes.target.value)
    tabs.push(target)
    buttons.push(button)
    button.addEventListener('click', function() {
        hide_all()
        show(target, button)
    })
    // show the first tab by default
    if (tabs.length == 1) {
        show(target, button)
    }
}


/**
 * event listener for onreadystatechange that displays error messages
 * from the server on the frontend, e.g. after submitting colors and stuff
 * @param {request} req 
 */
function status_listener(req, show_ok) {
    return function () {
        if (req.readyState != 4)
            return
        let status = req.responseText
        // no response and not 200, print code
        if (req.status != 200 && status == '') {
            status = req.status
        }
        // if everything is fine, just display a short note that it worked out
        if (show_ok && req.status == 200 && status == '') {
            status = 'success'
            if (hide_status_timeout !== null) {
                window.clearTimeout(hide_status_timeout)
            }
            hide_status_timeout = window.setTimeout(function() {
                document.getElementById('status').className = 'hidden'
            }, 1000)
        }
        if (status != '') {
            document.getElementById('status').className = ''
            document.getElementById('status').innerHTML = status
        }
    }
}


/**
 * asks the server about the current LED color and stores
 * it in variables. also calls refreshBorderColor to show
 * it in the frontend
 */
function load_color() {
    // put current color onto the frontend
    let color_req = new XMLHttpRequest()
    color_req.open('GET', '/color/get')
    color_req.onreadystatechange = function () {
        if (color_req.readyState != 4 || color_req.status != 200)
            return
        let color = JSON.parse(color_req.responseText)
        r = color['r']
        g = color['g']
        b = color['b']
        document.getElementById('r').value = r
        document.getElementById('g').value = g
        document.getElementById('b').value = b
        refreshBorderColor()
    }
    color_req.send()
}


function load_config() {
    // load config from server
    let config_req = new XMLHttpRequest()
    config_req.open('GET', '/config')
    config_req.onreadystatechange = function () {
        if (config_req.readyState != 4 || config_req.status != 200)
            return
        config = JSON.parse(config_req.responseText)
        // write keys into inputs, if available
        for (const key of Object.keys(config)) {
            const elem = document.getElementById(key)
            if (elem != null) {
                elem.value = config[key]
            }
        }
    }
    config_req.send()
}


/**
 * colorizes parts of the frontend to the colors of the
 * current user input
 */
function refreshBorderColor() {
    r = parseInt(document.getElementById('r').value)
    g = parseInt(document.getElementById('g').value)
    b = parseInt(document.getElementById('b').value)

    // change backgrounds
    const bgcolor = 'rgb(' + r + ',' + g + ',' + b + ')'
    document.getElementById('main').style.borderColor = bgcolor
    document.getElementById('nav').style.backgroundColor = bgcolor

    // make font black if background becomes too light
    if (r + g * 3 + b * 0.5 > 1000) {
        // dark text
        document.getElementById('main').className = 'dark'
    } else {
        document.getElementById('main').removeAttribute('class')
    }
}


/**
 * submit the current color of the input
 * to the server
 */
function submit(e) {
    r = parseInt(document.getElementById('r').value)
    g = parseInt(document.getElementById('g').value)
    b = parseInt(document.getElementById('b').value)

    if (isNaN(r)) r = 0
    if (isNaN(g)) g = 0
    if (isNaN(b)) b = 0

    const payload = { r: 0, g: 0, b: 0 }

    payload.r = parseInt(Math.min(config.clr_range, Math.max(0, r * config.clr_range / 255)))
    payload.g = parseInt(Math.min(config.clr_range, Math.max(0, g * config.clr_range / 255)))
    payload.b = parseInt(Math.min(config.clr_range, Math.max(0, b * config.clr_range / 255)))

    let req = new XMLHttpRequest()
    req.open('GET', '/color/set?r=' + payload.r + '&g=' + payload.g + '&b=' + payload.b, true)

    req.onreadystatechange = status_listener(req, false)

    req.send()

    refreshBorderColor()

    e.preventDefault()
    return false
}


/**
 * tell the server to stop and restart 
 */
function restart(e) {
    let req = new XMLHttpRequest()
    req.open('GET', '/restart')
    req.send()

    e.preventDefault()
    return false
}


/**
 * sends the configuration from the config
 * form to the server. restarting the
 * server might be needed for some options
 * like the port 
 */
function configure(e) {
    let req = new XMLHttpRequest()
    req.open('POST', '/config')

    const payload = {}
    const form = new FormData(document.getElementById('form_config'))
    for (const key of form.keys()) {
        const value = form.get(key)
        if (typeof value != 'number' && !value) {
            // if '', undefined, etc.
            continue
        }
        // some validation
        if (key == 'port') {
            if (value <= 0) {
                continue
            }
        }
        payload[key] = value
    }

    req.onreadystatechange = status_listener(req, true)

    console.log(payload)
    req.send(JSON.stringify(payload))

    e.preventDefault()
    return false
}

document.getElementById('form_static').addEventListener('submit', submit)
document.getElementById('submitconf').addEventListener('click', configure)
document.getElementById('restart').addEventListener('click', restart)

for (const id of ['r', 'g', 'b']) {
    document.getElementById(id).addEventListener('touchmove', refreshBorderColor)
    document.getElementById(id).addEventListener('mousemove', refreshBorderColor)
    document.getElementById(id).addEventListener('change', refreshBorderColor)
}

load_color()
load_config()
