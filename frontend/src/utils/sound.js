import { Howl } from "howler";

export const hoverSound = new Howl({
  src: ["/hover.wav"],
  volume: 0.35,
  html5: true,
});

export const clickSound = new Howl({
  src: ["/hover.wav"],
  volume: 0.4,
  html5: true,
});
