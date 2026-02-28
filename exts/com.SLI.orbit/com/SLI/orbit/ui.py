import math
import omni.ui as ui

#ORBIT UI
class OUI:

    def __init__(self,ext, title ="ORBIT CONTROLS"):
        self._ext = ext
        self._window = ui.Window(title, width=360, height = 280)
        self._a_model = ui.SimpleFloatModel(25.0)      
        self._e_model = ui.SimpleFloatModel(0.0)
        self._i_model = ui.SimpleFloatModel(0.0)      
        self._raan_model = ui.SimpleFloatModel(0.0)   
        self._argp_model = ui.SimpleFloatModel(0.0)   
        self._nu_model = ui.SimpleFloatModel(0.0)     

        with self._window.frame:
            with ui.VStack(spacing=8, height = 0):
                ui.Label("2BO - TWO BODY ORBIT (PROTOTYPE)", height=18)

                #MODELS
                self._mu_model = ui.SimpleFloatModel(float(ext.MU))
                self._r_model = ui.SimpleFloatModel(float(ext.R_ORBIT))
                self._dt_model = ui.SimpleFloatModel(float(ext.DT_SIM))
                # self._plane_model = ui.SimpleStringModel("xy")

                ui.Label("Gravitational Parameter μ (m^3/s^2)")
                ui.FloatField(model= self._mu_model)

                ui.Label("Orbit Radius r0 (m)")
                ui.FloatField(model = self._r_model)

                ui.Label("Integrator dt_sim (s)")
                ui.FloatField(model = self._dt_model)

                ui.Label("Orbit Plane")

                # self._plane_combo = ui.ComboBox(0,"xy","xz","yz")
                # self._plane_idx = ui.SimpleIntModel(0)
                # self._plane_combo = ui.ComboBox(0, "xy", "xz", "yz", model=self._plane_idx)
                # self._plane_idx = ui.SimpleIntModel(0)
                # self._plane_combo = ui.ComboBox(self._plane_idx, "xy", "xz", "yz")
                #self._plane_combo = ui.ComboBox(0, "xy", "xz", "yz")
                self._plane_combo = ui.ComboBox(0, "xy", "xz", "yz")
                ui.Spacer(height=6)
                ui.Label("Orbital Elements (optional)")

                ui.Label("Semi-major axis a (m)")
                ui.FloatField(model=self._a_model)

                ui.Label("Eccentricity e")
                ui.FloatField(model=self._e_model)

                ui.Label("Inclination i (deg)")
                ui.FloatField(model=self._i_model)

                ui.Label("RAAN Ω (deg)")
                ui.FloatField(model=self._raan_model)

                ui.Label("Arg of Perigee ω (deg)")
                ui.FloatField(model=self._argp_model)

                ui.Label("True Anomaly θ (deg)")
                ui.FloatField(model=self._nu_model)
                self._plane_idx_model = self._plane_combo.model.get_item_value_model()

                self._use_elements = ui.SimpleBoolModel(False)
                ui.CheckBox(model=self._use_elements)
                ui.Label("Use Orbital Elements (ignore radius/plane)")

                with ui.HStack(spacing = 8):
                    ui.Button("APPLY", clicked_fn = self._on_apply)
                    ui.Button("RESET",clicked_fn = self._on_reset)
                    ui.Button("PAUSE/PLAY", clicked_fn=self._on_pause_play)

                self._info = ui.Label("",height = 48)
                self._update_info()

    # def _on_plane_changed(self, _m):
    #     idx = int(self._plane_combo.model.get_value_as_int())
    #     plane = ["xy", "xz", "yz"][idx] if 0 <= idx <= 2 else "xy"
    #     self._plane_model.set_value(plane)

    def _update_info(self):
        mu = float(self._mu_model.get_value_as_float())
        r = float(self._r_model.get_value_as_float())
        if mu > 0 and r > 0:
            T = 2.0 * math.pi * math.sqrt((r ** 3) / mu)
            v = math.sqrt(mu / r)
            self._info.text = f"Estimated:\n  period ~ {T:.2f} s\n  speed  ~ {v:.2f} m/s"
        else:
            self._info.text = "Enter positive μ and r."

    def _on_apply(self):
        mu = float(self._mu_model.get_value_as_float())
        r = float(self._r_model.get_value_as_float())
        dt = float(self._dt_model.get_value_as_float())
        # plane = str(self._plane_model.get_value_as_string()).lower()

        # self._a_model    = ui.SimpleFloatModel(50.0)   
        # self._e_model    = ui.SimpleFloatModel(0.0)
        # self._i_model    = ui.SimpleFloatModel(0.0)    
        # self._raan_model = ui.SimpleFloatModel(0.0)   
        # self._argp_model = ui.SimpleFloatModel(0.0)   
        # self._nu_model   = ui.SimpleFloatModel(0.0)  

        if mu <= 0 or r <= 0:
            self._info.text = "μ and r must be > 0"
            return
        if dt <= 0:
            self._info.text = "dt_sim must be > 0"
            return
        # if plane not in ("xy", "xz", "yz"):
        #     self._info.text = "plane must be xy/xz/yz"
        #     return
        
        # idx = int(self._plane_idx.get_value_as_int())
        # plane = ["xy", "xz", "yz"][idx] if 0 <= idx <= 2 else "xy"

        #idx = int(self._plane_combo.model.get_value_as_int())

        use_elements = bool(self._use_elements.get_value_as_bool())
        if use_elements:
            a= float(self._a_model.get_value_as_float())
            e = float(self._e_model.get_value_as_float())
            inc = float(self._i_model.get_value_as_float())
            raan = float(self._raan_model.get_value_as_float())
            argp = float(self._argp_model.get_value_as_float())
            nu = float(self._nu_model.get_value_as_float())
            if a <= 0:
                self._info.text = "a must be > 0"
                return
            if e < 0 or e >= 1:
                self._info.text = "e must be in  [0,1)"
                return
            
            print("APPLY ELEMENTS: ", mu, a, e, inc, raan, argp, nu)
            self._ext.apply_elements(mu=mu, a=a, e=e, inc_deg=inc, raan_deg=raan, argp_deg=argp, nu_deg=nu)
        else:
            if r <= 0:
                self._info.text = "r must be > 0"
                return
            idx = int(self._plane_idx_model.get_value_as_int())
            plane = ["xy", "xz", "yz"][idx] if 0 <= idx <= 2 else "xy"
            print("UI plane idx =", idx, "plane =", plane)
            print("APPLY CIRCULAR:", mu, r, dt, plane)

            #APPLY TO EXTENSION
            self._ext.apply_orbit_settings(mu=mu, r_orbit=r, dt_sim=dt, plane=plane)
        self._update_info()

    def _on_reset(self):
        self._ext.reset_orbit_settings()

        #REFRESH UI MODELS FROM EXTENSION VALUES
        self._mu_model.set_value(float(self._ext.MU))
        self._r_model.set_value(float(self._ext.R_ORBIT))
        self._dt_model.set_value(float(self._ext.DT_SIM))

        #SET COMBO TO XY ON RESET
        # self._plane_combo.model.set_value(0)
        # self._plane_model.set_value("xy")
        #self._plane_idx.set_value(0)
        self._plane_idx_model.set_value(0)

        self._update_info()

    def _on_pause_play(self):
        tl = self._ext._timeline
        if tl.is_playing():
            tl.pause()
        else:
            tl.play()

    def destroy(self):
        if self._window:
            self._window.visible = False
            self._window = None