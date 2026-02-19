# Exporting Gerber Files from KiCad

## Generate Gerber Files

1. Open the PCB Editor
2. **File → Fabrication Outputs → Gerbers (.gbr)**
3. Set the output directory (e.g., `gerbers/`)
4. Select the following layers for a 2-layer board:
   - **F.Cu** — front copper
   - **B.Cu** — back copper
   - **F.SilkS** — front silkscreen
   - **B.SilkS** — back silkscreen
   - **F.Mask** — front solder mask
   - **B.Mask** — back solder mask
   - **Edge.Cuts** — board outline
5. Click **Plot**

## Generate Drill Files

1. In the same Gerber dialog, click **Generate Drill Files**
2. Use **Excellon** format
3. Set units to **millimeters**
4. Click **Generate Drill File**

## Submit to Fab House

Most fab houses (JLCPCB, PCBWay, OSH Park, etc.) accept a zip of all
the Gerber + drill files. Zip the entire output directory and upload it.

## Verify Before Ordering

Use a Gerber viewer to double-check the output before submitting:
- KiCad's standalone **GerbView** app
- Or an online viewer like [Gerber Viewer](https://www.pcbway.com/project/OnlineGerberViewer.html)
