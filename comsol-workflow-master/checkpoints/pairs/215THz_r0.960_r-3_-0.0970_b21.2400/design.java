/*
 * design.java
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

/** Model exported on Mar 15 2026, 09:40 by COMSOL 6.3.0.335. */
public class design {

  public static Model run() {
    Model model = ModelUtil.create("Model");

    model.modelPath("/cluster/scratch/jiayli/workspaces/param_sweep_pairs/215THz_r0.960_r-3_-0.0970_b21.2400");

    model.label("Model");

    model.param().set("a", "0.82 [um]");
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
         .set("table", new String[][]{{"0.06362508833144132 [um]", "0.0 [um]"}, {"0.2854290558342793 [um]", "-0.12805858034509052 [um]"}, {"0.2854290558342793 [um]", "0.12805858034509052 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol3", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3").label("Tri_2");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3")
         .set("table", new String[][]{{"0.06999174416572067 [um]", "0.12122925700539071 [um]"}, {"0.29179571166855867 [um]", "0.2492878373504812 [um]"}, {"0.06999174416572068 [um]", "0.37734641769557176 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol4", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4").label("Tri_3");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4")
         .set("table", new String[][]{{"-0.06999174416572065 [um]", "0.12122925700539078 [um]"}, {"-0.06999174416572058 [um]", "0.37734641769557176 [um]"}, {"-0.2917957116685586 [um]", "0.24928783735048132 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol5", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5").label("Tri_4");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5")
         .set("table", new String[][]{{"-0.06362508833144132 [um]", "7.791826077056722e-18 [um]"}, {"-0.2854290558342793 [um]", "0.12805858034509054 [um]"}, {"-0.2854290558342793 [um]", "-0.1280585803450905 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol6", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6").label("Tri_5");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6")
         .set("table", new String[][]{{"-0.06999174416572068 [um]", "-0.12122925700539063 [um]"}, {"-0.2917957116685587 [um]", "-0.249287837350481 [um]"}, {"-0.06999174416572082 [um]", "-0.37734641769557165 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol7", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7").label("Tri_6");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7")
         .set("table", new String[][]{{"0.06999174416572067 [um]", "-0.12122925700539071 [um]"}, {"0.06999174416572068 [um]", "-0.37734641769557176 [um]"}, {"0.29179571166855867 [um]", "-0.2492878373504812 [um]"}});
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
    model.component("comp1").selection("sel1").set(3);
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
    model.study("std1").feature("eig").set("neigsactive", true);
    model.study("std1").feature("eig").set("neigs", 8);

    model.component("comp1").mesh("mesh1").run();

    model.study("std1").createAutoSequences("all");

    model.sol("sol1").runAll();

    model.result().numerical().create("gev1", "EvalGlobal");
    model.result().numerical("gev1").label("Eigenfrequencies (ewfd)");
    model.result().numerical("gev1").set("data", "dset1");
    model.result().numerical("gev1").set("expr", new String[]{"ewfd.freq", "ewfd.Qfactor"});
    model.result().numerical("gev1").set("unit", new String[]{"THz", "1"});
    model.result().table().create("tbl1", "Table");
    model.result().numerical("gev1").set("table", "tbl1");
    model.result().numerical("gev1").run();
    model.result().numerical("gev1").setResult();
    model.result().dataset().create("cpl1", "CutPlane");
    model.result().dataset("cpl1").set("quickplane", "xy");
    model.result().create("pg1", "PlotGroup2D");
    model.result("pg1").label("2D Field (ewfd)");
    model.result("pg1").run();
    model.result("pg1").create("surf1", "Surface");
    model.result("pg1").feature("surf1").set("expr", "ewfd.normH");
    model.result("pg1").run();
    model.result().export().create("plot1", "pg1", "surf1", "Plot");
    model.result().export().create("img1", "pg1", "Image");
    model.result().export("img1").set("target", "file");
    model.result().create("pg2", "PlotGroup3D");
    model.result("pg2").run();
    model.result("pg2").label("3D Plot");
    model.result("pg2").create("mslc1", "Multislice");
    model.result("pg2").feature("mslc1").set("multiplanexmethod", "coord");
    model.result("pg2").feature("mslc1").set("xcoord", 0);
    model.result("pg2").feature("mslc1").set("multiplaneymethod", "coord");
    model.result("pg2").feature("mslc1").set("ycoord", 0);
    model.result("pg2").feature("mslc1").set("multiplanezmethod", "coord");
    model.result("pg2").feature("mslc1").set("zcoord", 0);
    model.result("pg2").feature("mslc1").set("expr", "ewfd.normE");
    model.result("pg2").run();
    model.result().export().create("img2", "pg2", "Image");
    model.result().export("img2").set("target", "file");

    return model;
  }

  public static void main(String[] args) {
    run();
  }

}
