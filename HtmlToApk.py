import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os

# ==========================================
# 1. THE COMPLETE MOBILE RUNTIME HTML TEMPLATE
# ==========================================
RUNTIME_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Hamid's Engine - Mobile Runtime (Full Physics)</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; user-select: none; -webkit-user-select: none; }
        body { overflow: hidden; background: #000; font-family: 'Inter', sans-serif; touch-action: none; }
        canvas { display: block; width: 100vw; height: 100vh; }
        
        /* HUD */
        #hud {
            position: absolute; top: 10px; left: 50%; transform: translateX(-50%);
            display: flex; gap: 15px; background: rgba(0,0,0,0.6); padding: 8px 20px;
            border-radius: 20px; color: white; font-weight: bold; pointer-events: none; z-index: 10;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);
        }
        .stat { color: #aaa; font-size: 12px; display: flex; flex-direction: column; align-items: center; }
        .val { color: #fff; font-size: 18px; font-variant-numeric: tabular-nums;}
        
        /* MOBILE CONTROLS */
        #mobile-ui { position: absolute; inset: 0; pointer-events: none; z-index: 5; display: none; }
        
        /* Left side: Movement Joystick Area */
        #move-zone { position: absolute; bottom: 20px; left: 20px; width: 150px; height: 150px; background: rgba(255,255,255,0.1); border-radius: 50%; pointer-events: auto; }
        #move-knob { position: absolute; top: 50px; left: 50px; width: 50px; height: 50px; background: rgba(255,255,255,0.4); border-radius: 50%; pointer-events: none; }
        
        /* Right side: Camera Drag Area */
        #look-zone { position: absolute; top: 0; right: 0; width: 50vw; height: 100vh; pointer-events: auto; }
        
        /* Action Buttons */
        .action-btn {
            position: absolute; background: rgba(255,255,255,0.2); border: 2px solid rgba(255,255,255,0.5);
            color: white; border-radius: 50%; font-weight: bold; pointer-events: auto;
            display: flex; justify-content: center; align-items: center; text-shadow: 1px 1px 2px #000;
        }
        .action-btn:active { background: rgba(255,255,255,0.5); transform: scale(0.95); }
        #shoot-btn { bottom: 40px; right: 40px; width: 80px; height: 80px; font-size: 16px; background: rgba(217, 68, 68, 0.4); border-color: #d94444; }
        #jump-btn { bottom: 140px; right: 80px; width: 60px; height: 60px; font-size: 12px; }

        /* Overlays */
        .overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.85); display: flex; flex-direction: column; justify-content: center; align-items: center; color: white; pointer-events: auto; z-index: 20; }
        .overlay h1 { font-size: 32px; margin-bottom: 20px; color: #d94444; text-align: center; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 20px rgba(217, 68, 68, 0.4);}
        .overlay button { padding: 15px 30px; font-size: 18px; background: #007fd4; color: white; border: none; border-radius: 8px; font-weight: bold; box-shadow: 0 4px 8px rgba(0, 127, 212, 0.3); }
        .overlay button:active { transform: translateY(2px); }
        
        /* Trigger Zone Text */
        .trigger-text { color: #4ec9b0 !important; text-shadow: 0 0 20px rgba(78, 201, 176, 0.4) !important; }
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div id="hud" class="hidden">
        <div class="stat">HP <span class="val" id="hud-hp">100</span></div>
        <div class="stat">AMMO <span class="val" id="hud-ammo">999</span></div>
        <div class="stat">ENEMIES <span class="val" id="hud-enemies">0</span></div>
    </div>

    <div id="mobile-ui">
        <div id="move-zone"><div id="move-knob"></div></div>
        <div id="look-zone"></div>
        <div class="action-btn" id="shoot-btn">FIRE</div>
        <div class="action-btn" id="jump-btn">JUMP</div>
    </div>

    <div id="start-overlay" class="overlay">
        <h1 id="start-title">MOBILE RUNTIME</h1>
        <button id="start-btn">TAP TO LOAD ENGINE</button>
    </div>

    <div id="loading-overlay" class="overlay hidden">
        <h1 style="color: #4ec9b0; text-shadow: 0 0 20px rgba(78,201,176,0.4);">DECODING ASSETS...</h1>
        <p id="loading-text" style="color: #888; letter-spacing: 1px;">Parsing Geometries & Audio...</p>
    </div>

    <div id="msg-overlay" class="overlay hidden">
        <h1 id="msg-title">GAME OVER</h1>
        <span style="color: #fff; opacity: 0.7; font-size: 14px; margin-top: 10px;">RELOAD PAGE TO RESTART</span>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    
    <script>
        // ==========================================
        // DATA INJECTION
        // ==========================================
        const GAME_DATA = __INJECT_JSON_DATA__;

        // ==========================================
        // ENGINE STATE & ASSET CACHES
        // ==========================================
        const state = {
            hp: 100, ammo: 999, playing: false, isFrozen: false, 
            audioCtx: null,
            shootSoundBuffer: null,
            floorSounds: {},     
            enemySounds: {},     
            modelCache: {}
        };

        // ==========================================
        // THREE.JS CORE SETUP
        // ==========================================
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87ceeb);
        scene.fog = new THREE.Fog(0x87ceeb, 0, 100);
        
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
        camera.rotation.order = 'YXZ';
        
        const renderer = new THREE.WebGLRenderer({ antialias: false });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.outputEncoding = THREE.sRGBEncoding;
        renderer.toneMapping = THREE.ACESFilmicToneMapping; 
        document.body.appendChild(renderer.domElement);

        const hemiLight = new THREE.HemisphereLight(0x87ceeb, 0x605040, 0.8);
        scene.add(hemiLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
        dirLight.position.set(50, 100, 50);
        dirLight.castShadow = true;
        scene.add(dirLight);

        const wallsGroup = new THREE.Group();
        const floorsGroup = new THREE.Group();
        const modelsGroup = new THREE.Group();
        scene.add(wallsGroup); scene.add(floorsGroup); scene.add(modelsGroup);
        
        const textureLoader = new THREE.TextureLoader();
        const gltfLoader = new THREE.GLTFLoader();

        // ==========================================
        // PLAYER PHYSICS
        // ==========================================
        const player = {
            pos: new THREE.Vector3(GAME_DATA.playerSpawn?.x || 10, 1.7, GAME_DATA.playerSpawn?.z || 10),
            vel: new THREE.Vector3(),
            rot: { x: 0, y: 0 },
            onGround: false,
            height: 1.7, radius: 0.3, stepDistance: 0
        };
        camera.position.copy(player.pos);

        // ==========================================
        // MOBILE INPUT CONTROLLERS
        // ==========================================
        const input = { moveX: 0, moveY: 0, jump: false, shoot: false };

        const moveZone = document.getElementById('move-zone');
        const moveKnob = document.getElementById('move-knob');
        const lookZone = document.getElementById('look-zone');
        let moveTouchId = null, lookTouchId = null;
        let lastLookX = 0, lastLookY = 0;

        // Joystick Logic
        moveZone.addEventListener('touchstart', e => {
            if(!state.playing) return; e.preventDefault();
            const touch = e.changedTouches[0]; moveTouchId = touch.identifier;
            updateMoveKnob(touch);
        });
        moveZone.addEventListener('touchmove', e => {
            if(!state.playing) return; e.preventDefault();
            for(let i=0; i<e.changedTouches.length; i++){
                if(e.changedTouches[i].identifier === moveTouchId) updateMoveKnob(e.changedTouches[i]);
            }
        });
        const resetMove = () => { moveTouchId = null; input.moveX = 0; input.moveY = 0; moveKnob.style.transform = `translate(0px, 0px)`; };
        moveZone.addEventListener('touchend', e => { for(let i=0; i<e.changedTouches.length; i++) if(e.changedTouches[i].identifier === moveTouchId) resetMove(); });
        moveZone.addEventListener('touchcancel', resetMove);

        function updateMoveKnob(t) {
            const rect = moveZone.getBoundingClientRect();
            const cx = rect.left + rect.width/2, cy = rect.top + rect.height/2;
            let dx = t.clientX - cx, dy = t.clientY - cy;
            const dist = Math.sqrt(dx*dx + dy*dy);
            const maxDist = 50;
            if(dist > maxDist) { dx = (dx/dist)*maxDist; dy = (dy/dist)*maxDist; }
            moveKnob.style.transform = `translate(${dx}px, ${dy}px)`;
            input.moveX = dx / maxDist; input.moveY = dy / maxDist;
        }

        // Camera Pan Logic
        lookZone.addEventListener('touchstart', e => {
            if(!state.playing) return; e.preventDefault();
            const touch = e.changedTouches[0]; lookTouchId = touch.identifier;
            lastLookX = touch.clientX; lastLookY = touch.clientY;
        });
        lookZone.addEventListener('touchmove', e => {
            if(!state.playing) return; e.preventDefault();
            for(let i=0; i<e.changedTouches.length; i++){
                const t = e.changedTouches[i];
                if(t.identifier === lookTouchId) {
                    const deltaX = t.clientX - lastLookX; const deltaY = t.clientY - lastLookY;
                    player.rot.y -= deltaX * 0.005;
                    player.rot.x -= deltaY * 0.005;
                    player.rot.x = Math.max(-Math.PI/2, Math.min(Math.PI/2, player.rot.x));
                    lastLookX = t.clientX; lastLookY = t.clientY;
                }
            }
        });
        const resetLook = () => { lookTouchId = null; };
        lookZone.addEventListener('touchend', resetLook); lookZone.addEventListener('touchcancel', resetLook);

        document.getElementById('jump-btn').addEventListener('touchstart', e => { e.preventDefault(); if(player.onGround && state.playing && !state.isFrozen) input.jump = true; });
        document.getElementById('shoot-btn').addEventListener('touchstart', e => { e.preventDefault(); if(state.playing && !state.isFrozen) shoot(); });

        // ==========================================
        // ASSET PRE-LOADER
        // ==========================================
        async function loadAudioBuffer(base64str) {
            try {
                const res = await fetch(base64str);
                const arrayBuffer = await res.arrayBuffer();
                return await state.audioCtx.decodeAudioData(arrayBuffer);
            } catch(e) { console.warn("Failed to decode audio", e); return null; }
        }

        async function loadGLTFModel(base64str) {
            return new Promise((resolve) => {
                gltfLoader.load(base64str, (gltf) => {
                    resolve(gltf.scene);
                }, undefined, (err) => {
                    console.warn("Failed to load GLTF", err);
                    resolve(null);
                });
            });
        }

        async function processAssets() {
            const loadingText = document.getElementById('loading-text');
            state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if(state.audioCtx.state === 'suspended') state.audioCtx.resume();

            loadingText.innerText = "Processing Audio Engine...";
            if (GAME_DATA.customShootSoundData) {
                state.shootSoundBuffer = await loadAudioBuffer(GAME_DATA.customShootSoundData);
            }

            loadingText.innerText = "Generating Acoustic Environment...";
            if (GAME_DATA.floorTextures) {
                for (let i = 0; i < GAME_DATA.floorTextures.length; i++) {
                    const tex = GAME_DATA.floorTextures[i];
                    if (tex && tex.soundData) {
                        state.floorSounds[i] = await loadAudioBuffer(tex.soundData);
                    }
                }
            }

            loadingText.innerText = "Parsing 3D Object Pool...";
            if (GAME_DATA.modelSources) {
                const keys = Object.keys(GAME_DATA.modelSources);
                for (let i=0; i < keys.length; i++) {
                    const source = GAME_DATA.modelSources[keys[i]];
                    if (source.url) {
                        const sceneObj = await loadGLTFModel(source.url);
                        if (sceneObj) state.modelCache[keys[i]] = sceneObj;
                    }
                }
            }

            loadingText.innerText = "Configuring Entities...";
            if (GAME_DATA.models) {
                for (let i = 0; i < GAME_DATA.models.length; i++) {
                    const m = GAME_DATA.models[i];
                    if (m.type === 'enemy') {
                        state.enemySounds[m.id] = { loop: null, death: null, node: null };
                        if (m.customSoundData) {
                            state.enemySounds[m.id].loop = await loadAudioBuffer(m.customSoundData);
                        }
                        if (m.customDeathSoundData) {
                            state.enemySounds[m.id].death = await loadAudioBuffer(m.customDeathSoundData);
                        }
                    }
                }
            }
        }

        // ==========================================
        // MAP BUILDER
        // ==========================================
        function buildMap() {
            const boxGeo = new THREE.BoxGeometry(2,2,2);
            const planeGeo = new THREE.PlaneGeometry(2,2);
            const wallMats = {}, floorMats = {};

            const getMat = (tex, cache, double) => {
                const key = tex.url || tex.color;
                if(cache[key]) return cache[key];
                
                let cfg = { roughness: 0.8 };
                if(tex.url) { 
                    const t = textureLoader.load(tex.url); 
                    t.wrapS = t.wrapT = THREE.RepeatWrapping; 
                    t.encoding = THREE.sRGBEncoding; 
                    cfg.map = t; 
                    cfg.color = 0xffffff;
                } else {
                    cfg.color = tex.color;
                }
                
                if(double) cfg.side = THREE.DoubleSide;
                const mat = new THREE.MeshStandardMaterial(cfg); 
                cache[key] = mat; 
                return mat;
            };

            const wBuckets = {};
            GAME_DATA.walls.forEach(w => {
                if(!wBuckets[w.texture]) wBuckets[w.texture] = [];
                const d = new THREE.Object3D(); d.position.set(w.x, w.y+1, w.z); d.updateMatrix();
                wBuckets[w.texture].push(d.matrix);
            });
            Object.keys(wBuckets).forEach(tIdx => {
                const tex = GAME_DATA.wallTextures[tIdx] || GAME_DATA.wallTextures[0];
                const mat = getMat(tex, wallMats, false);
                const mesh = new THREE.InstancedMesh(boxGeo, mat, wBuckets[tIdx].length);
                wBuckets[tIdx].forEach((m, i) => mesh.setMatrixAt(i, m));
                mesh.castShadow=true; mesh.receiveShadow=true; wallsGroup.add(mesh);
            });

            const fBuckets = {};
            GAME_DATA.floors.forEach(f => {
                if(!fBuckets[f.texture]) fBuckets[f.texture] = [];
                const d = new THREE.Object3D(); d.position.set(f.x, 0, f.z); d.rotation.x = -Math.PI/2; d.updateMatrix();
                fBuckets[f.texture].push(d.matrix);
            });
            Object.keys(fBuckets).forEach(tIdx => {
                const tex = GAME_DATA.floorTextures[tIdx] || GAME_DATA.floorTextures[0];
                const mat = getMat(tex, floorMats, true);
                const mesh = new THREE.InstancedMesh(planeGeo, mat, fBuckets[tIdx].length);
                fBuckets[tIdx].forEach((m, i) => mesh.setMatrixAt(i, m));
                mesh.receiveShadow=true; floorsGroup.add(mesh);
            });

            if(GAME_DATA.models) {
                GAME_DATA.models.forEach(m => {
                    const g = new THREE.Group();
                    g.position.set(m.position.x, m.position.y, m.position.z);
                    g.rotation.set(m.rotation.x, m.rotation.y, m.rotation.z);
                    g.scale.set(m.scale.x, m.scale.y, m.scale.z);

                    if(m.type === 'enemy') {
                        g.userData = { id: m.id, type: 'enemy', health: m.maxHealth||5, maxHealth: m.maxHealth||5, speed: m.speed||2, damage: m.damage||10 };
                        
                        let isCustomLoaded = false;
                        if ((m.visualType === 'custom' || (!m.visualType && m.customModelData)) && m.customModelData) {
                            gltfLoader.load(m.customModelData, (gltf) => {
                                const model = gltf.scene;
                                const box = new THREE.Box3().setFromObject(model);
                                const size = box.getSize(new THREE.Vector3());
                                if (size.y > 0) { const scaleFactor = 2.0 / size.y; model.scale.setScalar(scaleFactor); }
                                model.position.y = 0;
                                model.traverse(n => { if(n.isMesh){ n.castShadow=true; if(n.material) n.material=n.material.clone(); }});
                                g.add(model);
                            });
                            isCustomLoaded = true;
                        }

                        if (!isCustomLoaded) {
                            const bGeo = new THREE.BoxGeometry(1,2,1); const bMat = new THREE.MeshStandardMaterial({color:0xff0000});
                            const body = new THREE.Mesh(bGeo, bMat); body.position.y=1; body.castShadow=true; g.add(body);
                            const hGeo = new THREE.SphereGeometry(0.5,16,16); const hMat = new THREE.MeshStandardMaterial({color:0xff6666});
                            const head = new THREE.Mesh(hGeo, hMat); head.position.y=2.5; head.castShadow=true; g.add(head);
                        }

                        if (state.enemySounds[m.id] && state.enemySounds[m.id].loop) {
                            const gain = state.audioCtx.createGain();
                            gain.connect(state.audioCtx.destination);
                            gain.gain.value = 0;
                            const src = state.audioCtx.createBufferSource();
                            src.buffer = state.enemySounds[m.id].loop;
                            src.loop = true;
                            src.connect(gain);
                            src.start(0);
                            state.enemySounds[m.id].node = { src: src, gain: gain };
                        }
                    } else {
                        g.userData = { id: m.id, type: 'model' };
                        if (m.sourceId && state.modelCache[m.sourceId]) {
                            const clone = state.modelCache[m.sourceId].clone();
                            clone.traverse(n => { if(n.isMesh) { n.castShadow=true; n.receiveShadow=true; }});
                            g.add(clone);
                        }
                    }
                    modelsGroup.add(g);
                });
            }
        }

        // ==========================================
        // COLLISION & PHYSICS ENGINE
        // ==========================================
        function checkCollisions(pos, dir) {
            const pr = player.radius;
            
            // 1. Static Wall Checking
            for(let w of GAME_DATA.walls) {
                if(pos.x - pr <= w.x+1 && pos.x + pr >= w.x-1 && 
                   pos.y - player.height <= w.y+2 && pos.y + 0.2 >= w.y && 
                   pos.z - pr <= w.z+1 && pos.z + pr >= w.z-1) return true;
            }

            // 2. Custom Mesh Horizontal Checking (Exact Original Logic)
            if (dir) {
                const rayOrigin = player.pos.clone();
                rayOrigin.y -= 1.0; 
                const horizontalRaycaster = new THREE.Raycaster(rayOrigin, dir, 0, 0.5);
                const hits = horizontalRaycaster.intersectObjects(modelsGroup.children, true);
                if (hits.length > 0) return true;
            }

            return false;
        }

        function playFootstep() {
            if(!state.audioCtx) return;
            const px = Math.round(player.pos.x / 2) * 2;
            const pz = Math.round(player.pos.z / 2) * 2;
            const f = GAME_DATA.floors.find(fl => fl.x === px && fl.z === pz);
            
            const gain = state.audioCtx.createGain();
            if (f && state.floorSounds[f.texture]) {
                const src = state.audioCtx.createBufferSource();
                src.buffer = state.floorSounds[f.texture];
                gain.gain.value = 0.6;
                src.connect(gain); gain.connect(state.audioCtx.destination); src.start(0);
            } else {
                const osc = state.audioCtx.createOscillator();
                osc.type = 'triangle'; osc.frequency.setValueAtTime(150, state.audioCtx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(0.01, state.audioCtx.currentTime + 0.1);
                gain.gain.value = 0.2; osc.connect(gain); gain.connect(state.audioCtx.destination);
                osc.start(); osc.stop(state.audioCtx.currentTime + 0.1);
            }
        }

        function updateHUD() {
            document.getElementById('hud-hp').innerText = Math.ceil(state.hp);
            document.getElementById('hud-ammo').innerText = state.ammo;
            document.getElementById('hud-enemies').innerText = modelsGroup.children.filter(c => c.userData.type==='enemy' && c.visible).length;
        }

        function shoot() {
            if(state.ammo <= 0) return;
            state.ammo--; 
            
            if (state.shootSoundBuffer) {
                const src = state.audioCtx.createBufferSource();
                src.buffer = state.shootSoundBuffer;
                src.connect(state.audioCtx.destination);
                src.start(0);
            } else {
                const osc = state.audioCtx.createOscillator(); const gain = state.audioCtx.createGain();
                osc.connect(gain); gain.connect(state.audioCtx.destination); osc.type = 'square';
                osc.frequency.setValueAtTime(800, state.audioCtx.currentTime); osc.frequency.exponentialRampToValueAtTime(100, state.audioCtx.currentTime + 0.15);
                gain.gain.setValueAtTime(0.3, state.audioCtx.currentTime); gain.gain.exponentialRampToValueAtTime(0.01, state.audioCtx.currentTime + 0.15);
                osc.start(); osc.stop(state.audioCtx.currentTime + 0.15);
            }

            const ray = new THREE.Raycaster();
            const dir = new THREE.Vector3(0,0,-1).applyQuaternion(camera.quaternion);
            ray.set(camera.position, dir);
            
            const hits = ray.intersectObjects([...wallsGroup.children, ...modelsGroup.children], true);
            if(hits.length > 0) {
                let obj = hits[0].object;
                while(obj.parent && obj.parent !== scene && obj.parent !== modelsGroup) obj = obj.parent;
                if(obj.userData.type === 'enemy') {
                    obj.userData.health--;
                    obj.traverse(c => { if(c.material) { const old=c.material.color.getHex(); c.material.color.setHex(0xffffff); setTimeout(()=>c.material.color.setHex(old),50); }});
                    
                    if(obj.userData.health <= 0) {
                        obj.visible = false;
                        
                        const audioDat = state.enemySounds[obj.userData.id];
                        if (audioDat && audioDat.node) {
                            audioDat.node.gain.gain.value = 0;
                            try { audioDat.node.src.stop(); } catch(e){}
                        }

                        if (audioDat && audioDat.death) {
                            const src = state.audioCtx.createBufferSource();
                            src.buffer = audioDat.death;
                            src.connect(state.audioCtx.destination);
                            src.start(0);
                        }
                    }
                }
            }
            updateHUD();
        }

        function triggerCheck() {
            if(!GAME_DATA.triggers) return;
            for(let t of GAME_DATA.triggers) {
                if(Math.abs(player.pos.x - t.x) < 1 && Math.abs(player.pos.y - (t.y+1)) < 1 && Math.abs(player.pos.z - t.z) < 1) {
                    state.isFrozen = true;
                    const msgTitle = document.getElementById('msg-title');
                    msgTitle.innerText = t.text;
                    msgTitle.className = 'trigger-text'; 
                    document.getElementById('msg-overlay').classList.remove('hidden');
                    return;
                }
            }
        }

        // ==========================================
        // MAIN GAME LOOP
        // ==========================================
        const clock = new THREE.Clock();
        
        function animate() {
            requestAnimationFrame(animate);
            if(!state.playing) return;
            const delta = clock.getDelta();

            if(state.hp <= 0) {
                state.playing = false;
                const msgTitle = document.getElementById('msg-title');
                msgTitle.innerText = "GAME OVER";
                msgTitle.classList.remove('trigger-text');
                document.getElementById('msg-overlay').classList.remove('hidden');
                
                Object.values(state.enemySounds).forEach(e => {
                    if (e.node) e.node.gain.gain.value = 0;
                });
                return;
            }

            if(!state.isFrozen) {
                const moveSpeed = 5 * delta;
                
                // Horizontal Movement
                if(input.moveX !== 0 || input.moveY !== 0) {
                    const dir = new THREE.Vector3(input.moveX, 0, input.moveY).normalize();
                    dir.applyAxisAngle(new THREE.Vector3(0,1,0), player.rot.y);
                    const nextPos = player.pos.clone();
                    nextPos.x += dir.x * moveSpeed; nextPos.z += dir.z * moveSpeed;
                    
                    if(!checkCollisions(nextPos, dir)) { 
                        player.pos.x = nextPos.x; player.pos.z = nextPos.z; 
                        
                        if (player.onGround) {
                            player.stepDistance += moveSpeed;
                            if (player.stepDistance > 2.5) {
                                playFootstep();
                                player.stepDistance = 0;
                            }
                        }
                    }
                }

                // Vertical Gravity & Raycast Ground Detection (Restored Mesh Walking)
                player.vel.y -= 20 * delta;
                
                const downRay = new THREE.Raycaster(player.pos, new THREE.Vector3(0, -1, 0), 0, 10);
                const groundHits = downRay.intersectObjects(modelsGroup.children, true);
                
                let meshFloorY = -999;
                if (groundHits.length > 0) {
                    if (groundHits[0].distance <= player.height + 0.2 && groundHits[0].distance >= 0) {
                       meshFloorY = groundHits[0].point.y + player.height;
                    }
                }

                const standardFloor = 1.7;
                const groundLevel = Math.max(standardFloor, meshFloorY);
                let nextY = player.pos.y + player.vel.y * delta;
                
                if (nextY <= groundLevel) { 
                    player.pos.y = groundLevel; 
                    player.vel.y = 0; 
                    player.onGround = true; 
                } else { 
                    player.pos.y = nextY; 
                    player.onGround = false; 
                }

                if(input.jump && player.onGround) { 
                    player.vel.y = 6; 
                    player.onGround = false; 
                    input.jump = false;
                    player.pos.y += 0.1; // Unstuck offset
                }
                
                triggerCheck();
            }

            modelsGroup.children.forEach(e => {
                if(e.userData.type !== 'enemy' || !e.visible) return;
                
                const dist = e.position.distanceTo(player.pos);
                
                const audioDat = state.enemySounds[e.userData.id];
                if (audioDat && audioDat.node) {
                    let vol = dist < 25 ? Math.max(0, 1 - (dist / 25)) : 0;
                    audioDat.node.gain.gain.setTargetAtTime(vol * 0.3, state.audioCtx.currentTime, 0.1);
                }

                if(dist < 15) {
                    e.lookAt(player.pos.x, e.position.y, player.pos.z);
                    const dir = new THREE.Vector3().subVectors(player.pos, e.position).normalize();
                    e.position.add(dir.multiplyScalar(e.userData.speed * delta));
                    if(dist <= 2) { state.hp -= e.userData.damage * delta; updateHUD(); }
                }
            });

            camera.position.copy(player.pos);
            camera.rotation.y = player.rot.y;
            camera.rotation.x = player.rot.x;
            renderer.render(scene, camera);
        }

        // ==========================================
        // INITIALIZATION
        // ==========================================
        document.getElementById('start-btn').addEventListener('click', async () => {
            document.getElementById('start-overlay').classList.add('hidden');
            document.getElementById('loading-overlay').classList.remove('hidden');
            
            await processAssets();
            
            buildMap(); 
            updateHUD();
            
            document.getElementById('loading-overlay').classList.add('hidden');
            document.getElementById('hud').classList.remove('hidden');
            document.getElementById('mobile-ui').style.display = 'block';
            
            state.playing = true; 
            state.hp = 100; 
            state.isFrozen = false;
        });

        animate();
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>
"""

# ==========================================
# 2. TKINTER UI & LOGIC
# ==========================================
class MobileExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hamid's Engine Exporter (Mesh Physics Built-In)")
        self.root.geometry("520x280")
        self.root.resizable(False, False)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6)
        style.configure('TLabel', font=('Segoe UI', 10))

        # Main Frame
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(frame, text="Ultimate Mobile Runtime Exporter", font=('Segoe UI', 14, 'bold')).pack(pady=(0, 5))
        ttk.Label(frame, text="All Custom Textures, Audio, and Mesh Gravity Restored", font=('Segoe UI', 9, 'italic'), foreground="gray").pack(pady=(0, 15))

        # File tracking
        self.json_file_path = None
        self.lbl_file = ttk.Label(frame, text="No map selected.", foreground="gray", wraplength=450)
        self.lbl_file.pack(pady=10)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)

        self.btn_load = ttk.Button(btn_frame, text="1. Load JSON Map", command=self.load_json)
        self.btn_load.pack(side=tk.LEFT, expand=True, padx=5)

        self.btn_export = ttk.Button(btn_frame, text="2. Export to Mobile HTML", command=self.export_html, state=tk.DISABLED)
        self.btn_export.pack(side=tk.RIGHT, expand=True, padx=5)

    def load_json(self):
        filepath = filedialog.askopenfilename(
            title="Select Saved FPS Map",
            filetypes=[("JSON Files", "*.json")]
        )
        if filepath:
            self.json_file_path = filepath
            filename = os.path.basename(filepath)
            
            # Read file size
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            self.lbl_file.config(text=f"Ready: {filename} ({file_size_mb:.2f} MB)", foreground="green")
            self.btn_export.config(state=tk.NORMAL)

    def export_html(self):
        if not self.json_file_path:
            return

        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                map_data_str = f.read()
                # Validation check
                json.loads(map_data_str) 
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read or parse JSON file:\n{str(e)}")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Complete Mobile Runtime HTML",
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html")],
            initialfile="hamid_engine_mobile.html"
        )
        
        if not save_path:
            return

        try:
            # Direct injection
            final_html = RUNTIME_HTML_TEMPLATE.replace("__INJECT_JSON_DATA__", map_data_str)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(final_html)
                
            messagebox.showinfo("Success", f"Engine exported successfully!\n\nAll true mesh physics and textures are active.\nSaved to: {save_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save HTML file:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MobileExporterApp(root)
    root.mainloop()
