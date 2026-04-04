"""
Genera media/video-ventas.mp4 con voz (Edge TTS), portadas del pack y diapositivas
de marca. Ajustes para sonar más natural: voz es-ES-XimenaNeural, ritmo lento,
volumen suave, y pausas cortas entre frases (pydub + ffmpeg de imageio_ffmpeg).

Requiere: pip install -r scripts/requirements.txt
Ejecutar: python scripts/generar_video_ventas.py
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Raíz del proyecto (padre de /scripts)
ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = ROOT / "media"
IMAGES_DIR = ROOT / "images"
OUT_FILE = MEDIA_DIR / "video-ventas.mp4"
TMP_DIR = Path(__file__).resolve().parent / "_tmp_audio"

# Ximena (España): suele sonar más conversacional que otras neurales en castellano.
# Alternativas: "es-ES-AlvaroNeural" (voz masculina), "es-ES-ElviraNeural".
VOICE = "es-ES-XimenaNeural"
# Más lento = menos “rollo” continuo de máquina (prueba entre -15% y -22%)
TTS_RATE = "-20%"
# Tono suave; evita picos demasiado agudos
TTS_PITCH = "-2Hz"
# Un poco más de presencia sin gritar
TTS_VOLUME = "+6%"
# Pausa entre frases al unir audios (milisegundos); respiración más humana
TTS_PAUSE_MS = 260

W, H = 1280, 720

# Portadas en /images (nombre de archivo)
IMAGE_NAMES = [
    "mega-pack.png",
    "metodo-perro-habla.png",
    "codigo-maestro.png",
]

# Cada escena: ("file", "nombre.png", "") o ("slide", "título", "subtítulo")
# Debe coincidir en orden y cantidad con SCRIPT_PARTS.

SCENES: List[Tuple[str, str, str]] = [
    ("file", "mega-pack.png", ""),
    ("slide", "Más que leer el PDF", "Método, práctica y retos reales"),
    ("file", "metodo-perro-habla.png", ""),
    ("file", "codigo-maestro.png", ""),
    ("slide", "Bonus PDF + reto 21 días", "Guías útiles y guía de compras"),
    ("slide", "Reto 21 días", "Plan práctico para aplicar el método con tu mascota"),
    ("slide", "Obra nuestra", "Precio de inauguración · honestidad"),
    ("slide", "Tu opinión importa", "Revisiones · temas · promociones · sorteos"),
    ("slide", "Vuestras mascotas", "Protagonistas: fotos e historias reales"),
    ("slide", "Comunidad transparente", "Sin seguidores ficticios · Facebook"),
    ("slide", "Gracias por confiar", "Primeros seguidores que construyen con nosotros"),
    ("slide", "Vosotros decís", "Encuestas: salud, entreno, convivencia…"),
    ("slide", "Consejos que suman", "Comentarios para mejorar el material"),
    ("slide", "Compra en Hotmart", "PDF · vídeos · reto y guías · te leemos"),
]

SCRIPT_PARTS = [
    """Hola. Si amas a tu mascota, pero a veces notas que no la acabas de entender del todo, quédate un rato con nosotros.
Te presentamos Mundo Peludo. Es un pack digital para acercarte a su lenguaje, y a una forma de comunicar más clara, paso a paso, en el día a día.""",
    """No se trata solo de leer y cerrar el PDF. Lo que buscamos es un camino ordenado: método, profundidad, guías prácticas y retos.
Así lo que aprendas no se queda solo en teoría.""",
    """Aquí entra el enfoque del Método del Perro que Habla. Sirve para entender y potenciar la comunicación con tu mascota,
con ideas sobre lenguaje y botones de comunicación, cuando encajan en tu caso.""",
    """También está el Código Maestro de la Mente Canina. Ahí profundizamos en cómo piensa y se comporta,
y te acompañamos en el entrenamiento y en la convivencia de verdad.""",
    """Además vienen los bonus en PDF: longevidad, primeros auxilios, vocabulario útil, según tu compra.
Y el reto de veintiún días, más una guía de compras, para aplicar sin adivinar.""",
    """Con el calendario del reto y las guías, pasas de leer a hacer: pasos concretos para que el método se note en el día a día con tu mascota.""",
    """Todo esto es obra nuestra. Por eso podemos ofrecer un precio especial de inauguración.
Celebramos el lanzamiento, y el arranque de la comunidad Mundo Peludo, con honestidad.""",
    """Tu opinión nos importa de verdad. Con vuestros comentarios podremos plantear nuevas revisiones del material,
profundizar en lo que os interese, y diseñar promociones futuras. Y no lo decimos por decir: entre quienes nos siguen con cariño,
no descartamos regalar algunos de nuestros próximos libros, en sorteos o dinámicas en la página.""",
    """Nos encantaría que vuestras mascotas fueran protagonistas en Mundo Peludo: fotos, historias, vuestra voz.
Queremos un espacio compartido de verdad, no de postureo.""",
    """Este lanzamiento va junto a la inauguración de nuestra página en Facebook. No buscamos inflar números, ni seguidores de mentira.
Queremos una página transparente, con personas reales detrás, y conversación sincera.""",
    """Valoramos mucho a los primeros seguidores que se acercan ahora. Sois quienes nos ayudáis a construir el proyecto desde el principio,
con confianza, y con crítica cuando haga falta.""",
    """Allí haremos encuestas, y trataremos temas que os importen: entrenamiento, salud, alimentación, convivencia.
Así los contenidos y las ediciones futuras pueden ir más alineados con vosotros.""",
    """Compartiremos consejos prácticos. Leeremos opiniones. Y tendremos en cuenta los comentarios que suman,
para revisar el material, profundizar donde haga falta, y plantear promociones justas. También, cuando podamos, libros gratis para seguidores en sorteos o premios.""",
    """Soñamos con ver vuestras mascotas en la página. Creemos que compartir con respeto mejora un poco el mundo,
empezando por quienes nos dan la patita. Si te encaja, en Hotmart completas la compra: PDF y vídeos del pack, más las guías y el reto.
Esperamos que nuestra autoría sea de tu agrado. Déjanos comentarios, y cuéntanos qué te gustaría ver después. Gracias por estar ahí.""",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
        p = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / name
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _font_size(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    return int(getattr(font, "size", 16))


def render_brand_slide(title: str, subtitle: str = "") -> np.ndarray:
    """Diapositiva 1280x720: azul marino + dorado (marca), textos centrados."""
    img = Image.new("RGB", (W, H), "#152238")
    draw = ImageDraw.Draw(img)
    # Franja inferior dorada
    bar_h = 76
    draw.rectangle([0, H - bar_h, W, H], fill="#e4b421")
    # Línea sutil superior decorativa
    draw.rectangle([0, 0, W, 6], fill="#1e3354")

    font_brand = _font(22)
    font_title = _font(48)
    font_sub = _font(28)

    brand = "Mundo Peludo"
    bb = draw.textbbox((0, 0), brand, font=font_brand)
    bw = bb[2] - bb[0]
    draw.text(((W - bw) // 2, 42), brand, font=font_brand, fill="#e4b421")

    title_lines = textwrap.wrap(title.strip(), width=32)[:4]
    sub_lines = textwrap.wrap(subtitle.strip(), width=48)[:3] if subtitle else []

    line_h_title = int(_font_size(font_title) * 1.15)
    line_h_sub = int(_font_size(font_sub) * 1.2)
    block_title = len(title_lines) * line_h_title
    block_sub = len(sub_lines) * line_h_sub if sub_lines else 0
    gap = 28 if sub_lines else 0
    total_text = block_title + gap + block_sub
    y0 = (H - bar_h - total_text) // 2 + 10

    y = y0
    for line in title_lines:
        tb = draw.textbbox((0, 0), line, font=font_title)
        tw = tb[2] - tb[0]
        draw.text(((W - tw) // 2, y), line, font=font_title, fill="#faf9f7")
        y += line_h_title
    y += gap
    for line in sub_lines:
        sb = draw.textbbox((0, 0), line, font=font_sub)
        sw = sb[2] - sb[0]
        draw.text(((W - sw) // 2, y), line, font=font_sub, fill="#ebe8e0")
        y += line_h_sub

    # Texto en barra dorada (contraste oscuro)
    foot = "Educación · comunicación · bienestar"
    ff = _font(18)
    fb = draw.textbbox((0, 0), foot, font=ff)
    fw = fb[2] - fb[0]
    draw.text(((W - fw) // 2, H - bar_h + (bar_h - (fb[3] - fb[1])) // 2 - 2), foot, font=ff, fill="#152238")

    return np.array(img.convert("RGB"))


def _frame_from_file(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    im = im.resize((W, H), Image.LANCZOS)
    return np.array(im)


def _humanize_for_tts(text: str) -> str:
    """Normaliza espacios; el guion ya va en tono oral (frases cortas)."""
    t = text.strip()
    t = " ".join(t.split())
    for sep in (" — ", " —", "— "):
        t = t.replace(sep, ", ")
    return t


def _split_sentences(text: str) -> List[str]:
    """Parte en frases para insertar micro-pausas entre ellas (menos monólogo robótico)."""
    t = _humanize_for_tts(text)
    parts = re.split(r"(?<=[.!?])\s+", t)
    out = [p.strip() for p in parts if len(p.strip()) > 2]
    return out if out else [t]


def _ensure_ffmpeg_on_path() -> None:
    """pydub usa ffmpeg; MoviePy suele traerlo vía imageio_ffmpeg."""
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).is_file():
            folder = str(Path(exe).parent)
            if folder not in os.environ.get("PATH", ""):
                os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


async def _tts_one_sentence(text: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate=TTS_RATE,
        pitch=TTS_PITCH,
        volume=TTS_VOLUME,
    )
    await communicate.save(str(out_path))


async def _tts_to_file(text: str, out_path: Path, part_index: int) -> None:
    """Genera MP3: frase a frase + pausas cortas si pydub está disponible."""
    import edge_tts

    payload = _humanize_for_tts(text)
    sentences = _split_sentences(payload)

    if len(sentences) == 1:
        communicate = edge_tts.Communicate(
            sentences[0],
            VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
            volume=TTS_VOLUME,
        )
        await communicate.save(str(out_path))
        return

    try:
        from pydub import AudioSegment
    except ImportError:
        communicate = edge_tts.Communicate(
            payload,
            VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
            volume=TTS_VOLUME,
        )
        await communicate.save(str(out_path))
        return

    _ensure_ffmpeg_on_path()
    try:
        combined = AudioSegment.empty()
        pause = AudioSegment.silent(duration=TTS_PAUSE_MS)

        for j, sent in enumerate(sentences):
            chunk_path = TMP_DIR / f"part{part_index:02d}_s{j:02d}.mp3"
            await _tts_one_sentence(sent, chunk_path)
            combined += AudioSegment.from_mp3(str(chunk_path))
            if j < len(sentences) - 1:
                combined += pause
            try:
                chunk_path.unlink(missing_ok=True)
            except OSError:
                pass

        combined.export(str(out_path), format="mp3")
    except Exception as exc:
        print(
            "Aviso: pausas entre frases no disponibles (¿pydub/ffmpeg?). Se usa un solo audio.",
            exc,
            file=sys.stderr,
        )
        communicate = edge_tts.Communicate(
            payload,
            VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
            volume=TTS_VOLUME,
        )
        await communicate.save(str(out_path))


def _ensure_moviepy():
    try:
        from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
    except ImportError as e:
        print("Falta moviepy. Instala con: pip install -r scripts/requirements.txt", file=sys.stderr)
        raise e
    return AudioFileClip, ImageClip, concatenate_videoclips


def _build_file_map() -> Dict[str, Path]:
    m: Dict[str, Path] = {}
    for name in IMAGE_NAMES:
        p = IMAGES_DIR / name
        if not p.is_file():
            print("No se encuentra la imagen:", p, file=sys.stderr)
            sys.exit(1)
        m[name] = p
    return m


def scene_to_frame(scene: Tuple[str, str, str], file_map: Dict[str, Path]) -> np.ndarray:
    kind, a, b = scene
    if kind == "file":
        return _frame_from_file(file_map[a])
    if kind == "slide":
        return render_brand_slide(a, b)
    print("Tipo de escena desconocido:", kind, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    scenes = SCENES
    if len(scenes) != len(SCRIPT_PARTS):
        print("SCENES y SCRIPT_PARTS deben tener la misma longitud.", file=sys.stderr)
        sys.exit(1)

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    file_map = _build_file_map()
    AudioFileClip, ImageClip, concatenate_videoclips = _ensure_moviepy()

    print("Generando audios (Edge TTS: ritmo pausado + pausas entre frases)...")
    audio_files: list[Path] = []
    for i, part in enumerate(SCRIPT_PARTS):
        mp3 = TMP_DIR / f"part_{i:02d}.mp3"
        asyncio.run(_tts_to_file(part, mp3, i))
        audio_files.append(mp3)
        print(f"  OK parte {i + 1}/{len(SCRIPT_PARTS)}")

    clips = []
    for i, mp3 in enumerate(audio_files):
        audio = AudioFileClip(str(mp3))
        frame = scene_to_frame(scenes[i], file_map)
        ic = ImageClip(frame).set_duration(audio.duration).set_audio(audio)
        clips.append(ic)

    print("Montando vídeo (puede tardar varios minutos)...")
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(
        str(OUT_FILE),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger="bar",
    )
    final.close()
    for c in clips:
        c.close()

    print("Listo:", OUT_FILE)


if __name__ == "__main__":
    main()
