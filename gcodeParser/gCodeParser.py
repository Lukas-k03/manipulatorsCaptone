def generate_gcode(x=None, y=None, z=None, a=None, b=None, feedrate=100):

    #Generates a G-code command based on the given axis inputs.
    #Parameters:
        #x (float): Position for X-axis (optional)
        #y (float): Position for Y-axis (optional)
        #z (float): Position for Z-axis (optional)
        #a (float): Position for A-axis (optional)
        #b (float): Position for B-axis (optional)
    #Returns:
        #str: A formatted G-code command

    command = "G1"  #Linear move command in GCODE
    if x is not None:
        command += f" X{x}"
    if y is not None:
        command += f" Y{y}"
    if z is not None:
        command += f" Z{z}"
    if a is not None:
        command += f" A{a}"
    if b is not None:
        command += f" B{b}"
    
    #command += f" F{feedrate}"  # Append feed rate
    
    return command