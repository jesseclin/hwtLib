LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;
--
--    An unit which will extract selected circuit from parent on instantiation.
--    
ENTITY ExtractedUnit IS
    PORT(
        clk : IN STD_LOGIC;
        i : IN STD_LOGIC_VECTOR(7 DOWNTO 0);
        r0 : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
        sig_0 : IN BOOLEAN
    );
END ENTITY;

ARCHITECTURE rtl OF ExtractedUnit IS
    SIGNAL r0_0 : STD_LOGIC_VECTOR(7 DOWNTO 0) := X"00";
    SIGNAL r0_next : STD_LOGIC_VECTOR(7 DOWNTO 0);
BEGIN
    assig_process_r0: PROCESS(clk)
    BEGIN
        IF RISING_EDGE(clk) THEN
            IF sig_0 THEN
                r0_0 <= X"00";
            ELSE
                r0_0 <= r0_next;
            END IF;
        END IF;
    END PROCESS;
    r0 <= r0_0;
    assig_process_r0_next: PROCESS(i)
        VARIABLE tmpCastExpr_0 : UNSIGNED(7 DOWNTO 0);
    BEGIN
        tmpCastExpr_0 := UNSIGNED(i) + UNSIGNED'(X"01");
        r0_next <= STD_LOGIC_VECTOR(tmpCastExpr_0);
    END PROCESS;
END ARCHITECTURE;
LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;
--
--    An unit which will extract selected circuit from parent on instantiation.
--    
ENTITY ExtractedUnit_0 IS
    PORT(
        clk : IN STD_LOGIC;
        r1 : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
        sig_0 : IN BOOLEAN;
        sig_uForR0_r0 : IN STD_LOGIC_VECTOR(7 DOWNTO 0)
    );
END ENTITY;

ARCHITECTURE rtl OF ExtractedUnit_0 IS
    SIGNAL r1_0 : STD_LOGIC_VECTOR(7 DOWNTO 0) := X"00";
    SIGNAL r1_next : STD_LOGIC_VECTOR(7 DOWNTO 0);
BEGIN
    assig_process_r1: PROCESS(clk)
    BEGIN
        IF RISING_EDGE(clk) THEN
            IF sig_0 THEN
                r1_0 <= X"00";
            ELSE
                r1_0 <= r1_next;
            END IF;
        END IF;
    END PROCESS;
    r1 <= r1_0;
    assig_process_r1_next: PROCESS(sig_uForR0_r0)
        VARIABLE tmpCastExpr_1 : STD_LOGIC_VECTOR(7 DOWNTO 0);
        VARIABLE tmpCastExpr_0 : UNSIGNED(7 DOWNTO 0);
    BEGIN
        tmpCastExpr_1 := sig_uForR0_r0 XOR X"01";
        tmpCastExpr_0 := UNSIGNED(tmpCastExpr_1) + UNSIGNED'(X"01") + UNSIGNED(sig_uForR0_r0);
        r1_next <= STD_LOGIC_VECTOR(tmpCastExpr_0);
    END PROCESS;
END ARCHITECTURE;
LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;
ENTITY UnitWhichDynamicallyGeneratedSubunitsForRegistersWithExpr IS
    PORT(
        clk : IN STD_LOGIC;
        i : IN STD_LOGIC_VECTOR(7 DOWNTO 0);
        o : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
        rst_n : IN STD_LOGIC
    );
END ENTITY;

ARCHITECTURE rtl OF UnitWhichDynamicallyGeneratedSubunitsForRegistersWithExpr IS
    --
    --    An unit which will extract selected circuit from parent on instantiation.
    --    
    COMPONENT ExtractedUnit IS
        PORT(
            clk : IN STD_LOGIC;
            i : IN STD_LOGIC_VECTOR(7 DOWNTO 0);
            r0 : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
            sig_0 : IN BOOLEAN
        );
    END COMPONENT;
    --
    --    An unit which will extract selected circuit from parent on instantiation.
    --    
    COMPONENT ExtractedUnit_0 IS
        PORT(
            clk : IN STD_LOGIC;
            r1 : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
            sig_0 : IN BOOLEAN;
            sig_uForR0_r0 : IN STD_LOGIC_VECTOR(7 DOWNTO 0)
        );
    END COMPONENT;
    SIGNAL sig_uForR0_clk : STD_LOGIC;
    SIGNAL sig_uForR0_i : STD_LOGIC_VECTOR(7 DOWNTO 0);
    SIGNAL sig_uForR0_r0 : STD_LOGIC_VECTOR(7 DOWNTO 0);
    SIGNAL sig_uForR0_sig_0 : BOOLEAN;
    SIGNAL sig_uForR1_clk : STD_LOGIC;
    SIGNAL sig_uForR1_r1 : STD_LOGIC_VECTOR(7 DOWNTO 0);
    SIGNAL sig_uForR1_sig_0 : BOOLEAN;
    SIGNAL sig_uForR1_sig_uForR0_r0 : STD_LOGIC_VECTOR(7 DOWNTO 0);
BEGIN
    uForR0_inst: ExtractedUnit PORT MAP(
        clk => sig_uForR0_clk,
        i => sig_uForR0_i,
        r0 => sig_uForR0_r0,
        sig_0 => sig_uForR0_sig_0
    );
    uForR1_inst: ExtractedUnit_0 PORT MAP(
        clk => sig_uForR1_clk,
        r1 => sig_uForR1_r1,
        sig_0 => sig_uForR1_sig_0,
        sig_uForR0_r0 => sig_uForR1_sig_uForR0_r0
    );
    o <= sig_uForR1_r1;
    sig_uForR0_clk <= clk;
    sig_uForR0_i <= i;
    sig_uForR0_sig_0 <= rst_n = '0';
    sig_uForR1_clk <= clk;
    sig_uForR1_sig_0 <= rst_n = '0';
    sig_uForR1_sig_uForR0_r0 <= sig_uForR0_r0;
END ARCHITECTURE;
