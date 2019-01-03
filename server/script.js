'use strict'

let full_on = 20000

function submit(e)
{
    let r = document.getElementById('r').value
    let g = document.getElementById('g').value
    let b = document.getElementById('b').value

    if(r == '') r = 0
    if(g == '') r = 0
    if(b == '') r = 0

    r = parseInt(r)
    g = parseInt(g)
    b = parseInt(b)

    r = parseInt(Math.min(full_on, Math.max(0, r * full_on / 255)))
    g = parseInt(Math.min(full_on, Math.max(0, g * full_on / 255)))
    b = parseInt(Math.min(full_on, Math.max(0, b * full_on / 255)))

    let req = new XMLHttpRequest()
    req.open('GET', '/api/?r=' + r + '&g=' + g + '&b=' + b, true)    
    req.send()

    e.preventDefault()
    return false
}

document.getElementById('form').addEventListener('submit', submit)

