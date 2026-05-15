/*
 * InverseDesignModel_02.java
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

/** Model exported on Feb 3 2026, 19:11 by COMSOL 5.6.0.341. */
public class InverseDesignModel_02 {

  public static Model run() {
    Model model = ModelUtil.create("Model");

    model.modelPath("/Users/raywong/Desktop");

    model.label("InverseDesign.mph");

    model.param().set("a", "820 [nm]");
    model.param().set("b0", "245 [nm]");
    model.param().set("H", "200 [nm]");
    model.param().set("H_air", "lda0");
    model.param().set("lda0", "1550 [nm]");

    model.component().create("comp1", true);

    model.component("comp1").geom().create("geom1", 3);

    model.component("comp1").mesh().create("mesh1");

    model.component("comp1").geom("geom1").lengthUnit("\u00b5m");
    model.component("comp1").geom("geom1").create("wp1", "WorkPlane");
    model.component("comp1").geom("geom1").feature("wp1").set("unite", true);
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol1", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").label("Hex");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1")
         .set("table", new String[][]{{"a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"0", "a/sqrt(3)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}, 
         {"0", "-a/sqrt(3)"}, 
         {"a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol2", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol2").label("Tri_1");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol2").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol2")
         .set("table", new String[][]{{"0.1 [um]", "0 [um]"}, {"0.178 [um]", "-0.05 [um]"}, {"0.178 [um]", "0.05 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol3", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3").label("Tri_2");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3")
         .set("table", new String[][]{{"0.05 [um]", "0.1 [um]"}, {"0.16 [um]", "0.15 [um]"}, {"0.05 [um]", "0.2 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol4", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4").label("Tri_3");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4")
         .set("table", new String[][]{{"-0.06 [um]", "0.1[um]"}, {"-0.06[um]", "0.25[um]"}, {"-0.18[um]", "0.17[um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol5", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5").label("Tri_4");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5")
         .set("table", new String[][]{{"-0.12[um]", "0[um]"}, {"-0.27[um]", "0.08[um]"}, {"-0.27[um]", "-0.08[um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol6", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6").label("Tri_5");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6")
         .set("table", new String[][]{{"-0.06[um]", "-0.12 [um]"}, {"-0.24 [um]", "-0.21 [um]"}, {"-0.07 [um]", "-0.3 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol7", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7").label("Tri_6");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7")
         .set("table", new String[][]{{"0.07 [um]", "-0.12[um]"}, {"0.07 [um]", "-0.35 [um]"}, {"0.27 [um]", "-0.24 [um]"}});
    model.component("comp1").geom("geom1").create("ext1", "Extrude");
    model.component("comp1").geom("geom1").feature("ext1").setIndex("distance", "H/2", 0);
    model.component("comp1").geom("geom1").feature("ext1").selection("input").set("wp1");
    model.component("comp1").geom("geom1").create("wp2", "WorkPlane");
    model.component("comp1").geom("geom1").feature("wp2").set("quickz", "H/2");
    model.component("comp1").geom("geom1").feature("wp2").set("unite", true);
    model.component("comp1").geom("geom1").feature("wp2").geom().create("pol8", "Polygon");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8").label("Hex 1");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8")
         .set("table", new String[][]{{"a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"0", "a/sqrt(3)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}, 
         {"0", "-a/sqrt(3)"}, 
         {"a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}});
    model.component("comp1").geom("geom1").create("ext2", "Extrude");
    model.component("comp1").geom("geom1").feature("ext2").set("distance", new String[]{"H_air", "H_air*1.5"});
    model.component("comp1").geom("geom1").feature("ext2").set("scale", new double[][]{{1, 1}, {1, 1}});
    model.component("comp1").geom("geom1").feature("ext2").set("displ", new double[][]{{0, 0}, {0, 0}});
    model.component("comp1").geom("geom1").feature("ext2").set("twist", new int[]{0, 0});
    model.component("comp1").geom("geom1").feature("ext2").selection("input").set("wp2");
    model.component("comp1").geom("geom1").run();

    model.component("comp1").selection().create("sel1", "Explicit");
    model.component("comp1").selection("sel1").geom("geom1", 2);
    model.component("comp1").selection("sel1").set(3, 16, 21, 25, 37, 42, 47);
    model.component("comp1").selection("sel1").label("bottom");
    model.component("comp1").selection("sel1").set("groupcontang", true);

    model.component("comp1").material().create("mat1", "Common");
    model.component("comp1").material().create("mat2", "Common");
    model.component("comp1").material("mat1").propertyGroup().create("RefractiveIndex", "\u6298\u5c04\u7387");
    model.component("comp1").material("mat2").selection().set(1);
    model.component("comp1").material("mat2").propertyGroup().create("RefractiveIndex", "\u6298\u5c04\u7387");

    model.component("comp1").coordSystem().create("pml1", "PML");
    model.component("comp1").coordSystem("pml1").selection().set(3);

    model.component("comp1").physics().create("ewfd", "ElectromagneticWavesFrequencyDomain", "geom1");
    model.component("comp1").physics("ewfd").create("sctr1", "Scattering", 2);
    model.component("comp1").physics("ewfd").feature("sctr1").selection().set(10);
    model.component("comp1").physics("ewfd").create("pmc1", "PerfectMagneticConductor", 2);
    model.component("comp1").physics("ewfd").feature("pmc1").selection().named("sel1");
    model.component("comp1").physics("ewfd").create("pc1", "PeriodicCondition", 2);
    model.component("comp1").physics("ewfd").feature("pc1").selection().set(2, 5, 8, 32, 33, 34);
    model.component("comp1").physics("ewfd").create("pc2", "PeriodicCondition", 2);
    model.component("comp1").physics("ewfd").feature("pc2").selection().set(11, 12, 13, 29, 30, 31);
    model.component("comp1").physics("ewfd").create("pc3", "PeriodicCondition", 2);
    model.component("comp1").physics("ewfd").feature("pc3").selection().set(1, 4, 7, 50, 51, 52);

    model.component("comp1").view("view1").set("scenelight", false);
    model.component("comp1").view("view2").axis().set("xmin", -0.7867843508720398);
    model.component("comp1").view("view2").axis().set("xmax", 0.830589234828949);
    model.component("comp1").view("view2").axis().set("ymin", -0.6027438640594482);
    model.component("comp1").view("view2").axis().set("ymax", 0.7357029914855957);
    model.component("comp1").view("view3").axis().set("xmin", -6.29296152965253E-7);
    model.component("comp1").view("view3").axis().set("xmax", 6.29296152965253E-7);
    model.component("comp1").view("view3").axis().set("ymin", -5.207699018683343E-7);
    model.component("comp1").view("view3").axis().set("ymax", 5.207699018683343E-7);

    model.component("comp1").material("mat1").label("AIr");
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex").set("n", "");
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex").set("ki", "");
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex")
         .set("n", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex")
         .set("ki", new String[]{"0", "0", "0", "0", "0", "0", "0", "0", "0"});
    model.component("comp1").material("mat2").label("Mat");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("n", "");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("ki", "");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("n", "");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex").set("ki", "");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex")
         .set("n", new String[]{"3.3", "0", "0", "0", "3.3", "0", "0", "0", "3.3"});
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex")
         .set("ki", new String[]{"0", "0", "0", "0", "0", "0", "0", "0", "0"});

    model.study().create("std1");
    model.study("std1").create("eig", "Eigenfrequency");
    model.study("std1").feature("eig").set("shift", "c_const/1.55[um]");

    return model;
  }

  public static void main(String[] args) {
    run();
  }

}
