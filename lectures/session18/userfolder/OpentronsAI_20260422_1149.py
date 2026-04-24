from opentrons import protocol_api

metadata = {
    'protocolName': 'Serial Dilution - Red and Green Dyes',
    'author': 'OpentronsAI',
    'description': 'Vertical dilution with two dyes in opposite directions, horizontal factorial dilution, last row blank',
    'source': 'OpentronsAI'
}

requirements = {
    'robotType': 'Flex',
    'apiLevel': '2.25'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    deep_well_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 'D1')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_2ml_snapcap', 'D2')
    tiprack = protocol.load_labware('opentrons_flex_96_tiprack_1000ul', 'C1')
    
    # Load trash bin
    trash = protocol.load_trash_bin('A3')
    
    # Load pipette - using only left pipette as requested
    pipette = protocol.load_instrument(
        'flex_1channel_1000',
        'left',
        tip_racks=[tiprack]
    )
    
    # Define source locations in tube rack
    red_dye = tube_rack['A1']
    green_dye = tube_rack['A2']
    water = tube_rack['A3']
    
    # Protocol parameters
    diluent_volume = 1000  # 1 mL = 1000 µL
    transfer_volume = 500  # 0.5 mL = 500 µL
    
    # Step 1: Add 1 mL of water (diluent) to all wells except last row
    # Using rows A-G (indices 0-6), excluding row H (index 7) which is blank
    pipette.pick_up_tip()
    for row_idx in range(7):  # Rows A through G
        for col_idx in range(12):  # All 12 columns
            well = deep_well_plate.rows()[row_idx][col_idx]
            pipette.aspirate(diluent_volume, water)
            pipette.dispense(diluent_volume, well)
    pipette.drop_tip()
    
    # Step 2: Add 1 mL of water to last row (H) as blank
    pipette.pick_up_tip()
    for col_idx in range(12):
        well = deep_well_plate.rows()[7][col_idx]  # Row H
        pipette.aspirate(diluent_volume, water)
        pipette.dispense(diluent_volume, well)
    pipette.drop_tip()
    
    # Step 3: Vertical dilution - Red dye from top to bottom (Column 1)
    # Add red dye to A1 and perform serial dilution down column 1
    pipette.pick_up_tip()
    # Add red dye to A1
    pipette.aspirate(transfer_volume, red_dye)
    pipette.dispense(transfer_volume, deep_well_plate['A1'])
    pipette.mix(3, 750)  # Mix 3 times with 750 µL
    
    # Serial dilution down column 1 (A1 to G1, skip H1 as it's blank)
    for row_idx in range(6):  # A to F (0-5)
        source_well = deep_well_plate.rows()[row_idx][0]
        dest_well = deep_well_plate.rows()[row_idx + 1][0]
        pipette.aspirate(transfer_volume, source_well)
        pipette.dispense(transfer_volume, dest_well)
        pipette.mix(3, 750)
    pipette.drop_tip()
    
    # Step 4: Vertical dilution - Green dye from bottom to top (Column 12)
    # Add green dye to G12 and perform serial dilution up column 12
    pipette.pick_up_tip()
    # Add green dye to G12
    pipette.aspirate(transfer_volume, green_dye)
    pipette.dispense(transfer_volume, deep_well_plate['G12'])
    pipette.mix(3, 750)
    
    # Serial dilution up column 12 (G12 to A12, skip H12 as it's blank)
    for row_idx in range(6, 0, -1):  # G to B (6 down to 1)
        source_well = deep_well_plate.rows()[row_idx][11]
        dest_well = deep_well_plate.rows()[row_idx - 1][11]
        pipette.aspirate(transfer_volume, source_well)
        pipette.dispense(transfer_volume, dest_well)
        pipette.mix(3, 750)
    pipette.drop_tip()
    
    # Step 5: Horizontal factorial dilution across each row (columns 1-11)
    # For rows A through G, perform serial dilution from column 1 to column 11
    for row_idx in range(7):  # Rows A through G
        pipette.pick_up_tip()
        for col_idx in range(11):  # Columns 1-11 (transfer from col to col+1)
            source_well = deep_well_plate.rows()[row_idx][col_idx]
            dest_well = deep_well_plate.rows()[row_idx][col_idx + 1]
            pipette.aspirate(transfer_volume, source_well)
            pipette.dispense(transfer_volume, dest_well)
            pipette.mix(3, 750)
        pipette.drop_tip()
    
    protocol.comment('Serial dilution protocol complete!')
    protocol.comment('Red dye diluted vertically down column 1')
    protocol.comment('Green dye diluted vertically up column 12')
    protocol.comment('Factorial dilution performed horizontally across rows A-G')
    protocol.comment('Row H contains water blanks')