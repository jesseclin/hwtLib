LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;
--dynamically generated, for example loaded from file or builded from unit content
ENTITY SimpleComentedHwModule3 IS
    PORT(
        a : IN STD_LOGIC;
        b : OUT STD_LOGIC
    );
END ENTITY;

ARCHITECTURE rtl OF SimpleComentedHwModule3 IS
BEGIN
    b <= a;
END ARCHITECTURE;
