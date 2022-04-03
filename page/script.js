// src_base = 'subfolder/' or jsdelivr CDN
// defined in HTML

const langs = ["zh", "en"]

let lang = "zh"
if (!navigator.language.startsWith("zh")) {
  lang = "en"
  document.getElementById("lang-slider").value = 1
}
document.body.classList.add(lang)

document
  .getElementById("lang-slider-container")
  .addEventListener("click", function () {
    let slider = document.getElementById("lang-slider")
    document.body.classList.remove(langs[slider.value])
    slider.value = 1 - slider.value
    lang = langs[slider.value]
    document.body.classList.add(lang)
  })

const randomSeed = 1

let charData
const charNames = {
  en: [],
  zh: [],
}

let stats
let centeredNode
let centeredNodePrevPosition

const cy = cytoscape({
  container: document.getElementById("cy"), // container to render in
  elements: [],
  boxSelectionEnabled: false,
  minZoom: 0.1,
  maxZoom: 2.5, // auto ~0.5
  style: [
    // the stylesheet for the graph
    {
      selector: "node",
      style: {
        width: "80px",
        height: "80px",
        "background-fit": "contain",
        "background-color": "hsl(0, 0%, 90%)",
        //   'transition-property': "width, height, border-color",
        //   'transition-duration': "30ms"
      },
    },
    {
      selector: "edge",
      style: {
        width: 3,
        "line-color": "hsl(0, 0%, 75%)",
        opacity: 0.25,
        //   'transition-property': "width, line-color, opacity",
        //   'transition-duration': "80ms"
      },
    },
    {
      selector: ".selectedNode",
      style: {
        "border-width": 2,
        "border-color": "black",
        "border-style": "solid",
        width: "95px",
        height: "95px",
      },
    },
    {
      selector: ".connectedEdges",
      style: {
        "line-color": "hsl(0, 0%, 45%)",
        width: 4,
        opacity: 0.3,
        "z-index": 9,
      },
    },
    {
      selector: ".unconnectedEdges",
      style: {
        "line-color": "hsl(0, 0%, 85%)",
        width: 2,
        opacity: 0.15,
        "z-index": 0,
      },
    },
  ],
})

function getSelectedOption() {
  for (let el of document.querySelectorAll("input[type=radio]")) {
    if (el.checked) {
      return el.value
    }
  }
}

// let savedLayouts = {}
// let prevOption = getSelectedOption()

// function storeLayout() {
//     const data = cy.json();
//     const nodes = data.elements.nodes
//     const savedLayouts = {};
//     for (let n of nodes) {
//       savedLayouts[n.data.id] = n.position;
//     }
//     savedLayouts['pan'] = data.pan
//     savedLayouts['zoom'] = data.zoom
//     return savedLayouts;
// }

function gcd(a, b) {
  if (!b) {
    return a
  }
  return gcd(b, a % b)
}

function lcm(a, b) {
  return (a * b) / gcd(a, b)
}

function moveNodeTo(node, pos = "center") {
  let destination
  if (typeof pos === "object") {
    destination = pos
  } else if (pos === "center") {
    let box = cy.extent()
    destination = { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 }
  } else {
    console.log("invalid position")
  }

  node.animate({
    position: destination,
    queue: false,
    duration: 600,
    easing: "ease-in-out",
  })
}

function rotate(pos, center, angle) {
  let dx = pos.x - center.x
  let dy = pos.y - center.y
  let r = Math.sqrt(dx ** 2 + dy ** 2)
  let theta = Math.atan2(dy, dx) + angle // in radian
  let newX = center.x + r * Math.cos(theta)
  let newY = center.y + r * Math.sin(theta)
  return { x: newX, y: newY }
}

function rotateCircles() {
  const selectedNode = cy.$(".selectedNode")
  let levelFolds = {}
  for (let n of cy.$("node")) {
    // ignore 0 connection ones
    let l = selectedNode.edgesWith(n).length
    if (l > 0) {
      if (!levelFolds[l]) {
        levelFolds[l] = 1
      } else {
        levelFolds[l] += 1
      }
    }
  }

  let folds = Object.values(levelFolds)
    .map((x) => parseInt(x))
    .sort((a, b) => a - b)
  let maxFold = folds[folds.length - 1]
  let maxFold2 = folds[folds.length - 2]
  let levelRef = Object.keys(levelFolds).filter(
    (k) => levelFolds[k] == maxFold
  )[0]
  for (let n of cy.nodes()) {
    let l = selectedNode.edgesWith(n).length
    let currentFold = levelFolds[l]
    if (l != levelRef && l > 0) {
      let angle = 0
      if (folds.indexOf(currentFold) == folds.length - 2) {
        angle = Math.PI / lcm(currentFold, maxFold)
      } else if (folds.indexOf(currentFold) == folds.length - 3) {
        if (maxFold == maxFold2) {
          angle = (0.5 * Math.PI) / maxFold
        } else {
          angle = -Math.PI / maxFold
        }
      }
      // else if (folds.indexOf(currentFold) == folds.length - 4){
      //     angle = - Math.PI / maxFold
      // }
      else {
        angle = (-Math.random() * Math.PI) / maxFold
      }

      n.animate({
        position: rotate(n.position(), selectedNode.position(), angle),
        queue: false,
        duration: 600,
        easing: "ease-in-out",
      })
    }
  }
}

function getLayout(name) {
  let layoutOptions = {
    name: name,
    animate: "end",
    animationEasing: "ease-in-out",
    animationDuration: 700,
    stop: function () {
      // prevOption = getSelectedOption()
    },
  }
  let extraOptions = {}
  if (name == "fcose") {
    extraOptions = {
      // randomize: false,
      nodeSeparation: 150,
      nodeRepulsion: (node) => 100000, // node => 4500
      idealEdgeLength: (edge) => 80,
      edgeElasticity: (edge) => 0.05,
      ready: () => {
        if (cy.$(".selectedNodeTemp").length > 0) {
          // prevent different node size affecting layout
          cy.$(".selectedNodeTemp").addClass("selectedNode")
          cy.$(".selectedNodeTemp").removeClass("selectedNodeTemp")
        }
      },
    }
  }
  if (name == "avsdf") {
    extraOptions = {
      nodeSeparation: 95,
      stop: function () {
        if (cy.$(".selectedNode").length > 0) {
          centeredNode = cy.$(".selectedNode")
          centeredNodePrevPosition = Object.assign(
            {},
            cy.$(".selectedNode").position()
          )
          moveNodeTo(cy.$(".selectedNode"), "center")
        }
      },
    }
  }
  if (name == "concentric") {
    extraOptions = {
      levelWidth: (n) => 1,
      concentric: function (node) {
        let d = node.degree()
        let n = 1 // n <= 12
        if (d >= 13) n += 1
        if (d >= 16) n += 1
        if (d >= 18) n += 1
        if (d >= 21) n += 1
        // 1, 2, (3, 4)
        // l = Math.min(l, 3)
        return n
      },
    }
  }
  if (name == "concentricCustom") {
    extraOptions = {
      name: "concentric",
      concentric: function (node) {
        let selectedNode = cy.$(".selectedNode")
        if (selectedNode.id() == node.id()) {
          return 9
        } else {
          let l = selectedNode.edgesWith(node).length
          // 1, 2, (3, 4)
          // l = Math.min(l, 3)
          return l
        }
      },
      levelWidth: (n) => 1,
      // equidistant: true,
      // spacingFactor: 0.5,
      startAngle: 1.5 * Math.PI,
      stop: function () {
        rotateCircles()
      },
    }
  }
  // if (name == 'preset') {
  //     let sl = savedLayouts[params.layoutName]
  //     console.log(sl)
  //     extraOptions =  {
  //         pan: sl['pan'],
  //         zoom: sl['zoom'],
  //         positions: node => sl[node.id]
  //     }
  // }
  return cy.layout({ ...layoutOptions, ...extraOptions })
}

function setLayout(name, overwrite = false) {
  // reuse saved layout
  // (!overwrite && savedLayouts[name]) ? getLayout('preset', {layoutName: name}) :
  if (name === "concentric" && cy.$(".selectedNode").length > 0) {
    name = "concentricCustom"
  }
  if (name === "fcose") {
    if (cy.$(".selectedNode").length > 0) {
      cy.$(".selectedNode").addClass("selectedNodeTemp")
      cy.$(".selectedNode").removeClass("selectedNode")
    }
    Math.seedrandom(randomSeed, { global: true }) // overwrite RNG to get reproducible graph
  }

  if (centeredNodePrevPosition) {
    centeredNodePrevPosition = null
    centeredNode = null
  }

  let layout = getLayout(name)
  layout.run()
}

function unselectElements() {
  cy.$("node").removeClass("selectedNode")
  cy.$("node").removeClass("connectedNodes")
  cy.$("edge").removeClass("unconnectedEdges")
  cy.$("edge").removeClass("connectedEdges")
}

// copied from https://www.npmjs.com/package/popper-max-size-modifier
var maxSize = {
  name: "maxSize",
  enabled: true,
  phase: "main",
  requiresIfExists: ["offset", "preventOverflow", "flip"],
  fn: function fn(_ref) {
    var state = _ref.state,
      name = _ref.name,
      options = _ref.options
    var overflow = Popper.detectOverflow(state, options)

    var _ref2 = state.modifiersData.preventOverflow || {
        x: 0,
        y: 0,
      },
      x = _ref2.x,
      y = _ref2.y

    var _state$rects$popper = state.rects.popper,
      width = _state$rects$popper.width,
      height = _state$rects$popper.height

    var _state$placement$spli = state.placement.split("-"),
      basePlacement = _state$placement$spli[0]

    var widthProp = basePlacement === "left" ? "left" : "right"
    var heightProp = basePlacement === "top" ? "top" : "bottom"
    state.modifiersData[name] = {
      width: width - overflow[widthProp] - x,
      height: height - overflow[heightProp] - y,
    }
  },
}

const applyMaxSize = {
  name: "applyMaxSize",
  enabled: true,
  phase: "beforeWrite",
  requires: ["maxSize"],
  fn({ state }) {
    // The `maxSize` modifier provides this data
    const { width, height } = state.modifiersData.maxSize

    state.styles.popper = {
      ...state.styles.popper,
      maxWidth: `${width}px`,
      maxHeight: `${height}px`,
    }
  },
}

function makeTippyContent(node1, node2) {
  let text = ""
  for (const edge of node1.edgesTo(node2)) {
    text += `<div class="tip-title">${edge.data()["title_" + lang]}</div>`
    text += `<div class="tip-quote">${edge.data()["content_" + lang]}</div>`
  }
  if (text && node2.edgesTo(node1).length > 0)
    text += '<div class="tip-spacing"></div>'
  for (const edge of node2.edgesTo(node1)) {
    text += `<div class="tip-title">${edge.data()["title_" + lang]}</div>`
    text += `<div class="tip-quote">${edge.data()["content_" + lang]}</div>`
  }
  return text
}

function makeTippy(ele, text) {
  var ref = ele.popperRef()

  // Since tippy constructor requires DOM element/elements, create a placeholder
  var dummyDomEle = document.createElement("div")

  var tip = tippy(dummyDomEle, {
    popperOptions: {
      modifiers: [maxSize, applyMaxSize],
    },
    getReferenceClientRect: ref.getBoundingClientRect,
    trigger: "manual", // mandatory
    // dom element inside the tippy:
    content: function () {
      // function can be better for performance
      var div = document.createElement("div")

      div.innerHTML = text

      return div
    },
    // your own preferences:
    onHidden(instance) {
      instance.destroy()
    },
    // delay: [200, null], // doesn't seem to work, setTimeout manually
    theme: "light",
    arrow: true,
    placement: "auto",
    hideOnClick: true,
    sticky: "reference", // ?
    followCursor: "initial",
    // showOnCreate: true,
    // interactiveBorder: 20, // prevent hiding, doesn't seem to work (since not automatic)
    // if interactive:
    interactive: true,
    appendTo: document.body, // or append dummyDomEle to document.body
  })

  return tip
}

function makePopup(target, text, delay = 200) {
  target.tippy = makeTippy(target, text)
  target.showTimer = setTimeout(function () {
    target.tippy.show()
    cy.userZoomingEnabled(false)
    cy.userPanningEnabled(false)
  }, delay)
  // console.log('tippy')
  target.once("mouseout", (e) => {
    if (target.tippy) {
      target.tippy.hide()
    }
    clearTimeout(target.showTimer)
    cy.userZoomingEnabled(true)
    cy.userPanningEnabled(true)
  })
}

function showStats() {
  let totalNodes = cy.nodes().length
  let stats = []
  cy.nodes().forEach(function (ele) {
    let nodesIn = ele.incomers().filter((ele) => ele.isNode())
    let nodesOut = ele.outgoers().filter((ele) => ele.isNode())
    stats.push({
      id: ele.id(),
      indegree: nodesIn.length,
      outdegree: nodesOut.length,
      connections: nodesIn.union(nodesOut).length,
    })
  })
  let totalConnectios = stats.reduce((acc, cur) => acc + cur.connections, 0)
  let avgConnections = Math.round((10 * totalConnectios) / totalNodes) / 10
  document.getElementById("totalNodes").innerHTML = totalNodes
  document.getElementById("avgConnections").innerHTML = avgConnections
  return stats.sort((a, b) => b.connections - a.connections)
}

async function getJson(url) {
  let response = await fetch(url)
  let data = await response.json()
  return data
}

async function main() {
  charData = await getJson(`${src_base}char_data_min.json`)
  // create nodes
  for (const char of charData) {
    for (const l of langs) {
      charNames[l].push(char["name_" + l])
    }

    cy.add({
      group: "nodes",
      data: { id: char.name_en, name_en: char.name_en, name_zh: char.name_zh },
      style: {
        "background-image": char.img_url,
      },
    })
  }
  // create edges
  for (const sourceChar of charData) {
    for (const line of sourceChar.lines) {
      cy.add({
        group: "edges",
        data: {
          id: line.title_en, // A关于B
          source: sourceChar.name_en,
          target: line.target_en,
          ...line,
        },
      })
    }
  }

  for (const n of cy.$("node")) {
    if (n.degree() == 0) {
      n.remove()
    }
  }

  stats = showStats()

  setLayout(getSelectedOption())

  cy.$("edge").unpanify()
  cy.$("edge").unselectify()

  cy.on("tap", "node", function (event) {
    var target = event.target
    if (!target.hasClass("selectedNode")) {
      if (getSelectedOption() === "avsdf") {
        if (centeredNode != target) {
          if (centeredNode) {
            moveNodeTo(centeredNode, centeredNodePrevPosition) // replace prev centered one
          }
          centeredNode = target
          centeredNodePrevPosition = Object.assign({}, target.position())
          moveNodeTo(target, "center")
        }
      }

      cy.$(".selectedNode").removeClass("selectedNode")
      target.addClass("selectedNode")

      cy.$(".connectedEdges").removeClass("connectedEdges")
      cy.$("edge").addClass("unconnectedEdges")
      let targetEdges = target.connectedEdges()
      targetEdges.removeClass("unconnectedEdges")
      targetEdges.addClass("connectedEdges")

      cy.$(".connectedNodes").removeClass("connectedNodes")
      target.neighborhood("node").addClass("connectedNodes")

      if (getSelectedOption() === "concentric") {
        setLayout("concentricCustom")
      }
    }
  })

  cy.on("tap", function (ev) {
    if (ev.target === cy) {
      // tap bg
      unselectElements()
    }
  })

  cy.$("edge").on("mouseover", function (event) {
    let targetEdge = event.target
    if (targetEdge.hasClass("connectedEdges")) {
      let node1 = cy.$(".selectedNode")
      let node2 =
        targetEdge.source().id() == node1.id()
          ? targetEdge.target()
          : targetEdge.source()
      let text = makeTippyContent(node1, node2)
      makePopup(targetEdge, text)
    }
  })

  cy.$("node").on("mouseover", function (event) {
    let target = event.target
    if (target.hasClass("connectedNodes")) {
      let text = makeTippyContent(cy.$(".selectedNode"), target)
      makePopup(target, text, 500)
    }
  })

  document.querySelectorAll("input[type=radio]").forEach((r) => {
    r.addEventListener("input", function (e) {
      // savedLayouts[prevOption] = storeLayout()
      setLayout(e.target.value)
    })
  })

  document.querySelector("#refreshGraph").onclick = function (e) {
    // reset
    unselectElements()
    setLayout(getSelectedOption(), true)
  }

  fetch(
    "https://kois.pythonanywhere.com/plus?url=" +
      encodeURIComponent(window.location.href),
    { credentials: "include" }
  )
    .then((res) => res.text())
    .then((text) => console.log(text))
}

main()
