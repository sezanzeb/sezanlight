'use strict'

let r = 0
let g = 0
let b = 0
// this variable is set on all the clients and on the server as well.
// the range of values the raspberry accepts for each color channel
let config = { clr_range: 255 }

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

function status_listener(req) {
    return function () {
        if (req.readyState != 4)
            return
        let status = req.responseText
        // no response and not 200, print code
        if (req.status != 200 && status == '') {
            status = req.status
        }
        document.getElementById('status').innerHTML = status
    }
}

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
    }
    config_req.send()
}

function refreshBorderColor() {
    r = parseInt(document.getElementById('r').value)
    g = parseInt(document.getElementById('g').value)
    b = parseInt(document.getElementById('b').value)
    const color = 'rgb(' + r + ',' + g + ',' + b + ')'
    const elem = document.getElementById('main')
    elem.style.borderColor = color
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

    console.log(r, g, b)

    const payload = { r: 0, g: 0, b: 0 }

    payload.r = parseInt(Math.min(config.clr_range, Math.max(0, r * config.clr_range / 255)))
    payload.g = parseInt(Math.min(config.clr_range, Math.max(0, g * config.clr_range / 255)))
    payload.b = parseInt(Math.min(config.clr_range, Math.max(0, b * config.clr_range / 255)))

    let req = new XMLHttpRequest()
    req.open('GET', '/color/set?r=' + payload.r + '&g=' + payload.g + '&b=' + payload.b, true)

    req.onreadystatechange = status_listener(req)

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

    req.onreadystatechange = status_listener(req)

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
