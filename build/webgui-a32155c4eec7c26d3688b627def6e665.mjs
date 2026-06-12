
    function loadWebgui() {
        // webgui's dist is a Vite IIFE build that assigns a global `webgui`
        // var; it has no module exports, so it must be loaded as a classic
        // <script> and read off of window rather than import()-ed.
        if (window.webgui) return Promise.resolve(window.webgui);
        if (!window._webgui_loading) {
            window._webgui_loading = new Promise((resolve, reject) => {
                const s = document.createElement("script");
                s.src = "https://cdn.jsdelivr.net/npm/webgui@0.2.39/dist/webgui.js";
                s.onload = () => resolve(window.webgui);
                s.onerror = reject;
                document.head.appendChild(s);
            });
        }
        return window._webgui_loading;
    }

    // dat.gui (the control panel webgui adds, top-right) injects its stylesheet
    // into the main document <head>. When this widget is hosted by MyST it lives
    // inside a shadow root, and head styles do not cross the shadow boundary, so
    // the panel renders unstyled. Copy the dat.gui stylesheet into our shadow
    // root so it applies. No-op in a normal Jupyter page (no shadow root).
    function adoptDatGuiStyles(el) {
        const root = el.getRootNode();
        if (typeof ShadowRoot === 'undefined' || !(root instanceof ShadowRoot)) return;
        if (root.querySelector('style[data-webgui-datgui]')) return;
        let copied = false;
        for (const style of document.querySelectorAll('head style')) {
            const css = style.textContent || '';
            if (/\.dg[\s.,{>:]/.test(css)) {
                const clone = document.createElement('style');
                clone.setAttribute('data-webgui-datgui', '');
                clone.textContent = css;
                root.appendChild(clone);
                copied = true;
            }
        }
        return copied;
    }

    // The render data is normally the `value` trait itself. When `value` is a
    // string it is instead a URL to a JSON file holding the data: the static
    // MyST build offloads the (large) render data to a sidecar file next to the
    // notebook to keep pages small (see scripts/widgets_to_directives.py). Fetch
    // it in that case; otherwise use the value as-is.
    function resolveRenderData(value) {
        if (typeof value === 'string') {
            return fetch(value).then((resp) => resp.json());
        }
        return Promise.resolve(value);
    }

    // Interactive scene view (port of WebguiView in the legacy widget.ts).
    function renderScene(webgui, model, el) {
        el.classList.add('webgui-widget');
        // size the widget as requested from Python; the canvas container fills it

        const scene = new webgui.Scene();
        const container = document.createElement('div');
        container.style.width = model.get("width");
        container.style.height = model.get("height");
        el.appendChild(container);

        // defer to the next tick so the container is laid out before webgui
        // measures it (otherwise offsetHeight is read as ~0 -> tiny canvas)
        setTimeout(() => {
            resolveRenderData(model.get("value")).then((render_data) => {
                scene.init(container, render_data);
                scene.render();
                adoptDatGuiStyles(el);
                // dat.gui may inject its <style> a tick after construction; retry once.
                setTimeout(() => adoptDatGuiStyles(el), 100);
            });
        }, 0);

        // redraw: Python sets widget.value -> push new data into the scene
        model.on('change:value', () => {
            resolveRenderData(model.get("value")).then((render_data) => {
                scene.updateRenderData(render_data);
            });
        });
    }

    // Documentation view (port of WebguiDocuView): show a preview image and
    // only load the interactive scene + render data on click.
    function renderDocu(webgui, model, el) {
        const files = model.get("value");
        const container = document.createElement('div');
        container.className = 'webgui_container';
        container.style.width = '100%';
        container.innerHTML = `
            <img src="${files['preview']}" class="image">
            <div class="webgui_overlay webgui_tooltip">
                <span class="webgui_tooltiptext"> Click to load interactive WebGUI </span>
            </div>`;
        const div = document.createElement('div');
        div.appendChild(container);
        el.appendChild(div);

        container.addEventListener('click', () => {
            document.body.style.cursor = 'wait';
            fetch(files['render_data'])
                .then((resp) => resp.json())
                .then((render_data) => {
                    document.body.style.cursor = '';
                    const style = `width: ${el.clientWidth}px; height: ${el.clientHeight}px;`;
                    container.remove();
                    const pel = el.children[0];
                    pel.innerHTML = '';
                    pel.setAttribute('style', style);
                    const scene = new webgui.Scene();
                    scene.init(pel, render_data);
                    scene.render();
                    adoptDatGuiStyles(el);
                    setTimeout(() => adoptDatGuiStyles(el), 100);
                });
        });
    }

    async function render({ model, el }) {
        const webgui = await loadWebgui();
        const value = model.get("value");
        if (value && value.render_data !== undefined && value.preview !== undefined) {
            renderDocu(webgui, model, el);
        } else {
            renderScene(webgui, model, el);
        }
    }
    export default { render };
    