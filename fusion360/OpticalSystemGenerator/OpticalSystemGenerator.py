import adsk.core
import adsk.fusion
import traceback
import os

from claude_client import ClaudeClient
from schema import validate_and_fill
from params import ParameterManager
from builders.sensor_builder import SensorBuilder
from builders.lens_tube_builder import LensTubeBuilder
from builders.cage_builder import CageBuilder

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active Fusion design.')
            return

        root = design.rootComponent
        pm = ParameterManager(design)

        # Toggle Claude on/off while developing.
        use_claude = False

        if use_claude:
            api_key = os.environ.get('ANTHROPIC_API_KEY', '')
            if not api_key:
                raise ValueError('Missing ANTHROPIC_API_KEY env var')
            client = ClaudeClient(api_key)

            prompt = (
                'Generate parameters for an optical system. Return STRICT JSON only. '
                'Use mm units. Follow the schema exactly.'
            )
            params = client.generate_params(prompt)
        else:
            params = {
                'component': 'optical_system',
                'lens_tube': {
                    'inner_radius': 10,
                    'outer_radius': 12,
                    'tube_height': 40,
                    'lip_offset_from_sensor': 2,
                    'base_size': 50,
                    'base_thickness': 6,
                    'shell_thickness': 2,
                    'cutout_diameter': 20,
                    'cutout_offset_x': 0,
                    'cutout_offset_y': 0,
                    'lip_height': 2,
                    'lip_thickness': 2,
                    'clearance': 0.2,
                },
                'cage_system': {
                    'rod_spacing': 60,
                    'plate_distances': {'sensor_to_diffuser': 10, 'diffuser_to_lens': 15},
                    'sensor_object': {'width': 8, 'height': 5, 'depth': 2, 'offset_from_base': 2},
                    'diffuser_diameter': 12,
                    'lens_diameter': 20,
                    'plate_thickness': 4,
                    'plate_size': 80,
                    'rod_diameter': 6,
                    'mount_hole_diameter': 3.2,
                },
            }

        params = validate_and_fill(params)

        # --- Named parameters (mm) ---
        # Sensor
        pm.upsert('sensor_w', f"{params['cage_system']['sensor_object']['width']} mm", 'Sensor width')
        pm.upsert('sensor_h', f"{params['cage_system']['sensor_object']['height']} mm", 'Sensor height')
        pm.upsert(
            'sensor_d',
            f"{params['cage_system']['sensor_object'].get('depth', 2)} mm",
            'Sensor depth/thickness',
        )
        pm.upsert(
            'sensor_offset_z',
            f"{params['cage_system']['sensor_object']['offset_from_base']} mm",
            'Sensor Z offset from base ref',
        )

        # Lens tube housing
        lt = params['lens_tube']
        pm.upsert('inner_radius', f"{lt['inner_radius']} mm")
        pm.upsert('outer_radius', f"{lt['outer_radius']} mm")
        pm.upsert('tube_height', f"{lt['tube_height']} mm")
        pm.upsert('base_size', f"{lt['base_size']} mm")
        pm.upsert('base_thickness', f"{lt['base_thickness']} mm")
        pm.upsert('shell_thickness', f"{lt['shell_thickness']} mm")
        pm.upsert('cutout_diameter', f"{lt['cutout_diameter']} mm")
        pm.upsert('cutout_offset_x', f"{lt['cutout_offset_x']} mm")
        pm.upsert('cutout_offset_y', f"{lt['cutout_offset_y']} mm")
        pm.upsert('lip_offset_from_sensor', f"{lt['lip_offset_from_sensor']} mm")
        pm.upsert('lip_height', f"{lt['lip_height']} mm")
        pm.upsert('lip_thickness', f"{lt['lip_thickness']} mm")
        pm.upsert('clearance', f"{lt['clearance']} mm")

        # Derived (expressions reference other named parameters)
        pm.upsert('lip_inner_r', 'inner_radius + clearance', 'Lip inner radius')
        pm.upsert('lip_outer_r', 'lip_inner_r + lip_thickness', 'Lip outer radius')

        # Cage system
        cs = params['cage_system']
        pm.upsert('rod_spacing', f"{cs['rod_spacing']} mm")
        pm.upsert('sensor_to_diffuser', f"{cs['plate_distances']['sensor_to_diffuser']} mm")
        pm.upsert('diffuser_to_lens', f"{cs['plate_distances']['diffuser_to_lens']} mm")
        pm.upsert('diffuser_diameter', f"{cs['diffuser_diameter']} mm")
        pm.upsert('lens_diameter', f"{cs['lens_diameter']} mm")
        pm.upsert('plate_thickness', f"{cs['plate_thickness']} mm")
        pm.upsert('plate_size', f"{cs['plate_size']} mm")
        pm.upsert('rod_diameter', f"{cs['rod_diameter']} mm")
        pm.upsert('mount_hole_diameter', f"{cs['mount_hole_diameter']} mm")

        # --- Build geometry ---
        SensorBuilder(app, design, pm).build(root)
        LensTubeBuilder(app, design, pm).build(root)
        CageBuilder(app, design, pm).build(root)

        ui.messageBox('Optical system generated with named parameters (parametric).')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
