// 06_audio_engine.js - GBA 4-Channel Chiptune Engine (18 Tracks >= 12 min total, >= 45s per main track)
// PROVENANCE: Core synthesis & offline renderer lifted from beatsts-v1/src/06_audio_engine.js; expanded with 18 full-length tracks.

const AUDIO_CHANNELS = ['pulse1', 'pulse2', 'wave', 'noise'];

function midiToHz(m) { return 440 * Math.pow(2, (m - 69) / 12); }

const GBA_WAVETABLE = [
  0,1,2,3,5,7,9,11,13,14,15,15,14,12,10,8,
  7,5,3,2,1,0,1,2,4,6,8,10,12,13,11,8
];

// Repeat and transpose musical phrases to build full 45-55s multi-section GBA tracks
function buildPhraseTrack(bpm, loop, p1Phrases, p2Phrases, wvPhrases, nsPhrases) {
  const expand = (phrases, shifts) => {
    const out = [];
    for (let i = 0; i < shifts.length; i++) {
      const sh = shifts[i];
      const ph = phrases[i % phrases.length];
      for (const [m, d] of ph) out.push([m > 0 ? m + sh : 0, d]);
    }
    return out;
  };
  const shifts = [0, 0, 2, 0, 5, 4, 2, 0, -2, 0, 5, 7, 5, 4, 2, 0];
  return {
    bpm, loop,
    pulse1: expand(p1Phrases, shifts),
    pulse2: expand(p2Phrases, shifts),
    wave:   expand(wvPhrases, shifts),
    noise:  expand(nsPhrases, Array(shifts.length).fill(0))
  };
}

const MUSIC_TRACKS = {
  title: buildPhraseTrack(120, true,
    [[[72,1],[76,1],[79,1],[84,1],[79,1],[76,1],[74,2],[77,1],[81,1],[84,2],[79,2]], [[76,1],[79,1],[83,1],[84,1],[83,1],[79,1],[76,2],[74,2],[72,2],[79,2]]],
    [[[60,2],[64,2],[67,2],[65,2],[69,2],[67,2],[62,2]], [[64,2],[67,2],[69,2],[67,2],[64,2],[62,2],[60,2]]],
    [[[48,2],[48,2],[43,2],[45,2],[41,2],[43,2],[48,2]], [[48,2],[43,2],[45,2],[43,2],[48,2],[43,2],[48,2]]],
    [[[1,1],[0,1],[1,1],[1,1],[1,1],[0,1],[1,2],[1,1],[0,1],[1,2],[1,2]]]
  ),
  overworld_bread: buildPhraseTrack(116, true,
    [[[67,1],[71,1],[74,1],[76,1],[74,1],[71,1],[69,2],[67,1],[69,1],[71,2],[67,2]], [[71,1],[74,1],[76,1],[79,1],[76,1],[74,1],[72,2],[71,1],[69,1],[67,2],[64,2]]],
    [[[62,2],[64,2],[62,2],[60,2],[62,2],[64,2],[59,2]], [[64,2],[67,2],[65,2],[62,2],[64,2],[60,2],[59,2]]],
    [[[43,2],[48,2],[50,2],[45,2],[43,2],[48,2],[43,2]], [[43,2],[48,2],[45,2],[50,2],[43,2],[48,2],[43,2]]],
    [[[1,2],[0,2],[1,2],[0,2],[1,2],[0,2],[1,2]]]
  ),
  town_bread: buildPhraseTrack(108, true,
    [[[72,1],[74,1],[76,2],[79,1],[76,1],[74,2],[72,1],[74,1],[76,1],[72,1],[74,2]], [[76,1],[77,1],[79,2],[81,1],[79,1],[76,2],[74,2],[72,2],[74,2]]],
    [[[64,2],[67,2],[65,2],[62,2],[64,2],[67,2],[62,2]], [[64,2],[65,2],[67,2],[64,2],[62,2],[60,2],[62,2]]],
    [[[48,2],[43,2],[45,2],[47,2],[48,2],[43,2],[48,2]], [[48,2],[45,2],[43,2],[47,2],[48,2],[43,2],[48,2]]],
    [[[0,4],[1,2],[0,2],[0,4],[1,2]]]
  ),
  overworld_steam: buildPhraseTrack(104, true,
    [[[69,1],[72,1],[74,2],[76,1],[79,1],[76,2],[74,1],[72,1],[69,2],[67,2]], [[72,1],[74,1],[76,2],[79,1],[81,1],[79,2],[76,1],[74,1],[72,2],[69,2]]],
    [[[64,2],[67,2],[69,2],[67,2],[64,2],[62,2],[60,2]], [[64,2],[67,2],[69,2],[67,2],[64,2],[62,2],[60,2]]],
    [[[45,2],[48,2],[50,2],[48,2],[45,2],[43,2],[45,2]], [[45,2],[48,2],[50,2],[48,2],[45,2],[43,2],[45,2]]],
    [[[0,2],[1,2],[0,2],[1,2],[0,2],[1,2],[0,2]]]
  ),
  town_steam: buildPhraseTrack(100, true,
    [[[69,2],[72,1],[74,1],[76,2],[74,2],[72,1],[69,1],[67,2],[69,2]], [[72,2],[74,1],[76,1],[79,2],[76,2],[74,2],[72,2],[69,2]]],
    [[[60,2],[64,2],[67,2],[64,2],[62,2],[60,2],[57,2]], [[60,2],[64,2],[67,2],[64,2],[62,2],[60,2],[57,2]]],
    [[[45,2],[48,2],[52,2],[48,2],[47,2],[45,2],[43,2]], [[45,2],[48,2],[52,2],[48,2],[47,2],[45,2],[43,2]]],
    [[[1,4],[0,4],[1,4],[0,2]]]
  ),
  overworld_noodle: buildPhraseTrack(118, true,
    [[[74,1],[76,1],[79,1],[81,1],[79,1],[76,1],[74,1],[71,1],[72,2],[74,2],[76,2]], [[79,1],[81,1],[83,1],[86,1],[83,1],[81,1],[79,1],[76,1],[74,2],[76,2],[79,2]]],
    [[[67,2],[69,2],[67,2],[64,2],[65,2],[67,2],[69,2]], [[67,2],[69,2],[67,2],[64,2],[65,2],[67,2],[69,2]]],
    [[[50,2],[45,2],[47,2],[43,2],[45,2],[47,2],[50,2]], [[50,2],[45,2],[47,2],[43,2],[45,2],[47,2],[50,2]]],
    [[[1,1],[1,1],[0,1],[1,1],[1,1],[1,1],[0,1],[1,1],[1,2],[1,2],[1,2]]]
  ),
  town_noodle: buildPhraseTrack(110, true,
    [[[74,1],[76,1],[79,2],[76,1],[74,1],[71,2],[69,2],[71,2],[74,2]], [[76,1],[79,1],[81,2],[79,1],[76,1],[74,2],[72,2],[74,2],[76,2]]],
    [[[67,2],[64,2],[62,2],[60,2],[62,2],[64,2],[67,2]], [[67,2],[64,2],[62,2],[60,2],[62,2],[64,2],[67,2]]],
    [[[50,2],[47,2],[45,2],[43,2],[45,2],[47,2],[50,2]], [[50,2],[47,2],[45,2],[43,2],[45,2],[47,2],[50,2]]],
    [[[1,2],[0,2],[1,2],[0,2],[1,2],[0,2],[1,2]]]
  ),
  overworld_broth: buildPhraseTrack(98, true,
    [[[64,2],[67,1],[71,1],[72,2],[71,2],[69,2],[67,2],[64,2]], [[67,2],[71,1],[74,1],[76,2],[74,2],[72,2],[71,2],[67,2]]],
    [[[59,2],[60,2],[64,2],[62,2],[60,2],[59,2],[57,2]], [[59,2],[60,2],[64,2],[62,2],[60,2],[59,2],[57,2]]],
    [[[40,2],[43,2],[48,2],[47,2],[45,2],[43,2],[40,2]], [[40,2],[43,2],[48,2],[47,2],[45,2],[43,2],[40,2]]],
    [[[1,4],[0,4],[1,4],[0,2]]]
  ),
  town_broth: buildPhraseTrack(96, true,
    [[[64,2],[67,2],[69,2],[71,2],[69,2],[67,2],[64,2]], [[67,2],[69,2],[71,2],[74,2],[72,2],[71,2],[67,2]]],
    [[[59,2],[62,2],[64,2],[62,2],[60,2],[59,2],[55,2]], [[59,2],[62,2],[64,2],[62,2],[60,2],[59,2],[55,2]]],
    [[[40,2],[43,2],[45,2],[47,2],[45,2],[43,2],[40,2]], [[40,2],[43,2],[45,2],[47,2],[45,2],[43,2],[40,2]]],
    [[[0,4],[1,2],[0,2],[1,4],[0,2]]]
  ),
  battle_wild: buildPhraseTrack(126, true,
    [[[76,1],[75,1],[76,1],[79,1],[76,1],[72,1],[74,2],[76,1],[79,1],[83,1],[84,1],[79,2]], [[79,1],[78,1],[79,1],[83,1],[84,1],[83,1],[79,2],[76,1],[79,1],[81,1],[79,1],[76,2]]],
    [[[64,2],[67,2],[65,2],[62,2],[64,2],[67,2],[69,2]], [[64,2],[67,2],[65,2],[62,2],[64,2],[67,2],[69,2]]],
    [[[40,1],[40,1],[43,1],[43,1],[45,1],[45,1],[47,1],[47,1],[40,2],[43,2],[45,2]], [[40,1],[40,1],[43,1],[43,1],[45,1],[45,1],[47,1],[47,1],[40,2],[43,2],[45,2]]],
    [[[1,1],[1,1],[1,1],[0,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,2]]]
  ),
  battle_chef: buildPhraseTrack(128, true,
    [[[79,1],[81,1],[83,1],[84,1],[83,1],[81,1],[79,1],[76,1],[78,2],[79,2],[83,2]], [[84,1],[83,1],[81,1],[79,1],[78,1],[79,1],[81,1],[83,1],[84,2],[83,2],[79,2]]],
    [[[67,2],[69,2],[71,2],[67,2],[66,2],[67,2],[71,2]], [[67,2],[69,2],[71,2],[67,2],[66,2],[67,2],[71,2]]],
    [[[43,1],[43,1],[45,1],[45,1],[47,1],[47,1],[43,2],[42,2],[43,2],[47,2]], [[43,1],[43,1],[45,1],[45,1],[47,1],[47,1],[43,2],[42,2],[43,2],[47,2]]],
    [[[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,2],[1,2],[1,2]]]
  ),
  battle_rival: buildPhraseTrack(128, true,
    [[[74,1],[77,1],[81,1],[80,1],[77,1],[74,1],[76,2],[79,1],[83,1],[81,2],[77,2]], [[77,1],[81,1],[84,1],[83,1],[81,1],[77,1],[79,2],[81,1],[84,1],[83,2],[79,2]]],
    [[[62,2],[65,2],[69,2],[64,2],[67,2],[69,2],[65,2]], [[62,2],[65,2],[69,2],[64,2],[67,2],[69,2],[65,2]]],
    [[[38,1],[38,1],[41,1],[41,1],[45,1],[45,1],[40,2],[43,2],[45,2],[41,2]], [[38,1],[38,1],[41,1],[41,1],[45,1],[45,1],[40,2],[43,2],[45,2],[41,2]]],
    [[[1,1],[0,1],[1,1],[1,1],[1,1],[0,1],[1,2],[1,1],[1,1],[1,2],[1,2]]]
  ),
  battle_champion: buildPhraseTrack(132, true,
    [[[84,1],[83,1],[84,1],[88,1],[86,1],[84,1],[83,1],[81,1],[79,2],[83,2],[84,2],[88,2]], [[88,1],[86,1],[84,1],[83,1],[81,1],[79,1],[81,1],[83,1],[84,2],[86,2],[88,2],[91,2]]],
    [[[72,2],[71,2],[72,2],[76,2],[74,2],[72,2],[71,2],[76,2]], [[72,2],[71,2],[72,2],[76,2],[74,2],[72,2],[71,2],[76,2]]],
    [[[48,1],[48,1],[47,1],[47,1],[45,1],[45,1],[43,1],[43,1],[48,2],[47,2],[48,2],[52,2]], [[48,1],[48,1],[47,1],[47,1],[45,1],[45,1],[43,1],[43,1],[48,2],[47,2],[48,2],[52,2]]],
    [[[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,1],[1,2],[1,2],[1,2],[1,2]]]
  ),
  postgame: buildPhraseTrack(112, true,
    [[[72,2],[76,1],[79,1],[83,2],[84,2],[83,1],[79,1],[76,2],[74,2]], [[76,2],[79,1],[83,1],[86,2],[84,2],[83,1],[79,1],[76,2],[72,2]]],
    [[[60,2],[64,2],[67,2],[71,2],[69,2],[67,2],[62,2]], [[60,2],[64,2],[67,2],[71,2],[69,2],[67,2],[62,2]]],
    [[[48,2],[43,2],[45,2],[47,2],[48,2],[43,2],[48,2]], [[48,2],[43,2],[45,2],[47,2],[48,2],[43,2],[48,2]]],
    [[[1,2],[0,2],[1,2],[1,2],[1,2],[0,2],[1,2]]]
  ),
  victory: {
    bpm: 144, loop: false,
    pulse1: [[72,1],[76,1],[79,1],[84,3],[79,1],[84,4]],
    pulse2: [[60,1],[64,1],[67,1],[72,3],[67,1],[72,4]],
    wave:   [[48,3],[43,1],[48,6]],
    noise:  [[1,1],[1,1],[1,1],[1,3],[1,1],[1,4]]
  },
  healing: {
    bpm: 128, loop: false,
    pulse1: [[76,1],[79,1],[83,1],[84,3]],
    pulse2: [[64,1],[67,1],[71,1],[72,3]],
    wave:   [[48,3],[52,3]],
    noise:  [[0,6]]
  },
  evolution: {
    bpm: 140, loop: false,
    pulse1: [[67,1],[71,1],[74,1],[76,1],[79,1],[83,1],[86,2],[88,3]],
    pulse2: [[55,1],[59,1],[62,1],[64,1],[67,1],[71,1],[74,2],[76,3]],
    wave:   [[43,2],[47,2],[50,2],[55,5]],
    noise:  [[1,2],[1,2],[1,2],[1,5]]
  },
  credits: buildPhraseTrack(114, true,
    [[[72,2],[76,1],[79,1],[81,2],[79,2],[77,2],[76,2],[74,2],[72,2]], [[76,2],[79,1],[81,1],[84,2],[83,2],[81,2],[79,2],[76,2],[72,2]]],
    [[[60,2],[64,2],[65,2],[64,2],[62,2],[60,2],[59,2],[60,2]], [[60,2],[64,2],[65,2],[64,2],[62,2],[60,2],[59,2],[60,2]]],
    [[[48,4],[41,4],[43,4],[48,4]], [[48,4],[41,4],[43,4],[48,4]]],
    [[[1,2],[0,2],[1,2],[0,2],[1,2],[0,2],[1,2],[0,2]]]
  )
};

const SFX_DEFS = {
  menu_move:       { bpm: 300, pulse1: [[84,1]], pulse2: [], wave: [], noise: [] },
  menu_select:     { bpm: 280, pulse1: [[79,1],[84,2]], pulse2: [], wave: [], noise: [] },
  menu_back:       { bpm: 280, pulse1: [[76,1],[72,2]], pulse2: [], wave: [], noise: [] },
  hit_normal:      { bpm: 260, pulse1: [[60,1]], pulse2: [], wave: [[40,1]], noise: [[1,2]] },
  hit_super:       { bpm: 280, pulse1: [[72,1],[79,1],[84,2]], pulse2: [], wave: [], noise: [[1,2]] },
  hit_weak:        { bpm: 240, pulse1: [[55,2]], pulse2: [], wave: [], noise: [[1,1]] },
  plating_set:     { bpm: 220, pulse1: [[72,1],[76,1],[79,2]], pulse2: [[60,2]], wave: [], noise: [] },
  plating_success: { bpm: 200, pulse1: [[72,1],[76,1],[79,1],[84,3]], pulse2: [[64,3],[72,3]], wave: [[48,6]], noise: [[1,1]] },
  plating_fail:    { bpm: 200, pulse1: [[67,1],[64,1],[60,2]], pulse2: [], wave: [], noise: [[1,1]] },
  level_up:        { bpm: 240, pulse1: [[72,1],[74,1],[76,1],[79,1],[84,3]], pulse2: [[60,4]], wave: [], noise: [] },
  heal:            { bpm: 220, pulse1: [[76,1],[79,1],[84,2]], pulse2: [[64,4]], wave: [], noise: [] },
  door:            { bpm: 260, pulse1: [[64,1],[69,1]], pulse2: [], wave: [], noise: [[1,1]] }
};

function renderSequenceOffline(seq, sampleRate = 22050) {
  const stepSec = 60 / (seq.bpm || 120) / 2;
  const countSteps = arr => (arr || []).reduce((s, n) => s + n[1], 0);
  const totalSteps = Math.max(
    1,
    countSteps(seq.pulse1), countSteps(seq.pulse2), countSteps(seq.wave), countSteps(seq.noise)
  );
  const totalSamples = Math.max(1, Math.floor(totalSteps * stepSec * sampleRate));
  const out = new Float32Array(totalSamples);

  function renderPulse(notes, duty, amp) {
    if (!notes || !notes.length) return;
    let t = 0;
    for (const [midi, dur] of notes) {
      const start = Math.floor(t * stepSec * sampleRate);
      const end = Math.min(totalSamples, Math.floor((t + dur) * stepSec * sampleRate));
      if (midi > 0) {
        const hz = midiToHz(midi);
        const period = sampleRate / hz;
        for (let i = start; i < end; i++) {
          const ph = (i % period) / period;
          const env = 1 - ((i - start) / Math.max(1, end - start)) * 0.35;
          out[i] += (ph < duty ? 1 : -1) * amp * env;
        }
      }
      t += dur;
    }
  }

  function renderWave(notes, amp) {
    if (!notes || !notes.length) return;
    let t = 0;
    for (const [midi, dur] of notes) {
      const start = Math.floor(t * stepSec * sampleRate);
      const end = Math.min(totalSamples, Math.floor((t + dur) * stepSec * sampleRate));
      if (midi > 0) {
        const hz = midiToHz(midi);
        const period = sampleRate / hz;
        for (let i = start; i < end; i++) {
          const idx = Math.floor(((i % period) / period) * 32) & 31;
          const s = (GBA_WAVETABLE[idx] / 7.5) - 1;
          out[i] += s * amp;
        }
      }
      t += dur;
    }
  }

  function renderNoise(notes, amp) {
    if (!notes || !notes.length) return;
    let t = 0;
    let lfsr = 0x7FFF;
    for (const [on, dur] of notes) {
      const start = Math.floor(t * stepSec * sampleRate);
      const end = Math.min(totalSamples, Math.floor((t + dur) * stepSec * sampleRate));
      if (on > 0) {
        for (let i = start; i < end; i++) {
          if (i % 6 === 0) {
            const bit = ((lfsr >> 0) ^ (lfsr >> 1)) & 1;
            lfsr = (lfsr >> 1) | (bit << 14);
          }
          const env = Math.max(0, 1 - (i - start) / Math.max(1, (end - start) * 0.5));
          out[i] += ((lfsr & 1) ? 1 : -1) * amp * env;
        }
      }
      t += dur;
    }
  }

  renderPulse(seq.pulse1, 0.5, 0.18);
  renderPulse(seq.pulse2, 0.25, 0.12);
  renderWave(seq.wave, 0.18);
  renderNoise(seq.noise, 0.10);

  return {
    samples: out,
    durationSec: totalSamples / sampleRate,
    channelsUsed: AUDIO_CHANNELS.slice()
  };
}

function renderTrackOffline(trackId, sampleRate = 22050) {
  const tr = MUSIC_TRACKS[trackId];
  if (!tr) return null;
  return renderSequenceOffline(tr, sampleRate);
}

function renderSfxOffline(sfxId, sampleRate = 22050) {
  const sfx = SFX_DEFS[sfxId];
  if (!sfx) return null;
  return renderSequenceOffline(sfx, sampleRate);
}

const AudioEngine = {
  ctx: null,
  volume: 0.5,
  currentTrack: null,
  currentSource: null,
  muted: false,
  bufferCache: {},

  ensureCtx() {
    if (this.ctx) return this.ctx;
    try {
      const AC = typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext);
      if (AC) this.ctx = new AC();
    } catch (e) {}
    return this.ctx;
  },

  playMusic(trackId) {
    if (this.currentTrack === trackId) return;
    this.currentTrack = trackId;
    if (this.muted || this.volume <= 0) return;
    const ctx = this.ensureCtx();
    if (!ctx) return;
    try {
      if (ctx.state === 'suspended') ctx.resume();
      if (this.currentSource) { try { this.currentSource.stop(); } catch (e) {} }
      const rendered = this.bufferCache[trackId] || (this.bufferCache[trackId] = renderTrackOffline(trackId, 22050));
      if (!rendered) return;
      const buf = ctx.createBuffer(1, rendered.samples.length, 22050);
      buf.getChannelData(0).set(rendered.samples);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.loop = !!MUSIC_TRACKS[trackId].loop;
      const gain = ctx.createGain();
      gain.gain.value = this.volume * 0.4;
      src.connect(gain);
      gain.connect(ctx.destination);
      src.start();
      this.currentSource = src;
    } catch (e) {}
  },

  playSfx(sfxId) {
    if (this.muted || this.volume <= 0) return;
    const ctx = this.ensureCtx();
    if (!ctx) return;
    try {
      if (ctx.state === 'suspended') ctx.resume();
      const rendered = renderSfxOffline(sfxId, 22050);
      if (!rendered) return;
      const buf = ctx.createBuffer(1, rendered.samples.length, 22050);
      buf.getChannelData(0).set(rendered.samples);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      const gain = ctx.createGain();
      gain.gain.value = this.volume * 0.6;
      src.connect(gain);
      gain.connect(ctx.destination);
      src.start();
    } catch (e) {}
  }
};
