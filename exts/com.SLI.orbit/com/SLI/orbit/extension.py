import math
import os

import omni.ext
import omni.usd
import omni.kit.app
import omni.timeline
from pxr import UsdGeom, Gf

class SLIOrbitExtension(omni.ext.IExt):
    #CONFIG
    #DEFINE ORBITING BODIES
    '''
    THIS USES RK4 ODE SOLVER FOR ORBITAL MECHANICS
    '''
    SPHERE_PATH = "/World/Sphere"
    CUBE_PATH = "/World/Cube"

    CENTER = (0.0,0.0,0.0)
    R_ORBIT = 25.0
    MU=980.665
    DT_SIM = 1.0/120.0
    AUTO_OPEN_USD = True
    USD_FILENAME = "orbitTest1.usd"

    def on_startup(self,ext_id: str):
        self._ext_id = ext_id
        self._app = omni.kit.app.get_app()
        self._usd= omni.usd.get_context()
        self._timeline = omni.timeline.get_timeline_interface()

        self._update_sub = None
        self._stage_sub =  None
        self._accum = 0.0
        self._t_sphere = None
        self._t_cube = None

        v_circ = math.sqrt(self.MU / self.R_ORBIT)
        self._r = (self.R_ORBIT, 0.0, 0.0)
        self._v = (0.0, v_circ, 0.0)

        if self.AUTO_OPEN_USD:
            usd_path = self._packaged_usd_path(self.USD_FILENAME)
            if usd_path and os.path.exists(usd_path):
                print(f"[com.SLI.orbit] Opening USD: {usd_path}")
                self._usd.open_stage(usd_path)
            else:
                print(f"[com.SLI.orbit] AUTO_OPEN_USD=True but USD not found: {usd_path}")

        self._stage_sub = self._usd.get_stage_event_stream().create_subscription_to_pop(self._on_stage_event)

        self._rebind_ops()

        self._update_sub = self._app.get_update_event_stream().create_subscription_to_pop(self._on_update)

        self._timeline.play()

        T= 2.0 * math.pi * math.sqrt((self.R_ORBIT ** 3) / self.MU)
        print(f"[com.SLI.orbit] Startup OK. Orbit period ~ {T:.2f}s. Disable extension to stop.")

    def on_shutdown(self):
        if self._update_sub:
            self._update_sub.unsubscribe()
            self._update_sub = None
        if self._stage_sub:
            self._stage_sub.unsubscribe()
            self._stage_sub = None

        self._t_sphere = None
        self._t_cube = None
        print("[com.SLI.orbit] Shutdown.")

    def _on_stage_event(self,_evt):
        self._rebind_ops()
    
    def _rebind_ops(self):
        stage = self._usd.get_stage()
        if stage is None:
            self._t_sphere = None
            self._t_cube = None
            return

        self._t_cube = self._get_translate_op(stage, self.CUBE_PATH)
        self._t_sphere = self._get_translate_op(stage, self.SPHERE_PATH)

        if self._t_sphere is not None:
            try:
                self._t_sphere.Set(Gf.Vec3d(0.0, 0.0, 0.0))
            except Exception:
                self._t_sphere = None
    
    def _get_translate_op(self,stage,path: str):
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            return None
        xf = UsdGeom.Xformable(prim)
        for op in xf.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                return op
        return xf.AddTranslateOp()
    
    # def _package_usd_path(self, filename: str):
    #     prim = stage.GetPrimAtPath(path)
    #     if not prim or not prim.IsValid():
    #         return None
    #     xf = UsdGeom.Xformable(prim)
    #     for op in xf.GetOrderedXformOps():
    #         if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
    #             return op
    #     return xf.AddTranslateOp()
    
    def _packaged_usd_path(self, filename: str):
        ext_mgr = self._app.get_extension_manager()
        root = ext_mgr.get_extension_path(self._ext_id)
        if not root:
            return None
        return os.path.join(root,"data",filename)
    
    def _on_update(self,e):
        if not self._timeline.is_playing():
            return
        
        #CUBE NOT PRESENT YET
        if self._t_cube is None:
            return
        dt = float(e.payload.get("dt",0.0))
        if dt <= 0.0:
            return
        
        self._accum += dt 
        while self._accum >= self.DT_SIM:
            self._r, self._v = self._rk4_step(self._r, self._v, self.DT_SIM)
            self._accum -= self.DT_SIM
        try:
            self._t_cube.Set(Gf.Vec3d(*self._r))
        except Exception:
            self._t_cube = None
            self._rebind_ops()

    def _accel(self,pos):
        dx = pos[0] - self.CENTER[0]
        dy = pos[1] - self.CENTER[1]
        dz = pos[2] - self.CENTER[2]
        r2 = dx * dx + dy * dy + dz * dz
        if r2 < 1e-12:
            return (0.0,0.0,0.0)
        r = math.sqrt(r2)
        s = -self.MU / (r ** 3)
        return (s * dx, s * dy, s* dz)
    
    def _rk4_step(self, r, v, dt):
        def add(a,b):
            return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
        def mul(s,a):
            return (s*a[0], s*a[1], s*a[2])
        
        a1 = self._accel(r); k1r, k1v = v, a1
        r2 = add(r,mul(0.5* dt,k1r))
        v2 = add(v, mul(0.5 * dt, k1v))
        a2 = self._accel(r2); k2r, k2v = v2, a2

        r3 = add(r, mul(0.5 * dt, k2r))
        v3 = add(v, mul(0.5 * dt, k2v))
        a3 = self._accel(r3); k3r, k3v = v3, a3

        r4 = add(r, mul(dt, k3r))
        v4 = add(v, mul(dt, k3v))
        a4 = self._accel(r4); k4r, k4v = v4, a4

        r_next = add(r, mul(dt / 6.0, add(add(k1r, mul(2.0, k2r)), add(mul(2.0, k3r), k4r))))
        v_next = add(v, mul(dt / 6.0, add(add(k1v, mul(2.0, k2v)), add(mul(2.0, k3v), k4v))))
        return r_next, v_next
        



