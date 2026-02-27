# GeneTropica Conservation Visualization
# Load and color structure by conservation score (B-factor)

load 5ZQK_conservation.pdb, protein
bg_color white

# Color by conservation (B-factor): blue = conserved, red = variable
spectrum b, blue_white_red, protein, minimum=10, maximum=90

# Show binding site residues as sticks
select binding_site, resi 533+663+664+737+794
show sticks, binding_site
color yellow, binding_site and name CA

# Label key residues
label binding_site and name CA, "  %s%s" % (resn, resi)
set label_size, 14
set label_color, black

# Set view
orient
zoom protein, 5

# Ray trace for publication quality
set ray_opaque_background, on
ray 2400, 2400
png conservation_map.png, dpi=300
