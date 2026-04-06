% BU PROGRAM FCM ÝLE CLUSTER AYIRIYOR, PSO ÝLE CLUSTER MERKEZLERÝNÝ TUR ÝÇÝN SIRALIYOR
% ÇÝFTLER ÝÇÝN ÜYELÝK DEÐERLERÝNÝ ALIYOR VE ÜYELÝK FARKI EN AZ OLAN OLAN
% ELEMANI BAÐLANTI ADAYI OLARAK SEÇÝYOR
% VE O NOKTALARI CLUSTER SIRALARIN SON VE ÝLK NOKTASI OLARAK ÖTELEYÝP
% BAÐLANTIYI GERÇEKLEÞTÝRÝYOR.
% ÝPTAL EDÝLEN KISIMDA ÝSE ALFA DEÐERÝNDEN KÜÇÜK FARKA SAHÝP ELEMANLARI
% ADAY OLARAK SEÇÝYOR.
clear all;
close all;
sayaccluster=1;
for GENEL=6:10
sayacdeney=1; 
for DENEY=1:30
CLUSTER_SAYISI=GENEL;

% NESÝL SAYISINI DA CLUSTER SAYISINA GÖRE ÝÇERÝ GÖNDERÝP DEÐÝÞTÝR
% CLUSTER 2=3000 NESÝL, CLUSTER 3=1500 NESÝL, CLUSTER 4=1000 NESIL
% CLUSTER SIRALARINI BELÝRLE HANGÝ SIRA ÝLE TUR OLUÞTURACAK KONUMSAL
% BÝRLEÞTÝRME ÝÇÝN

% DENEY ÝÇÝN GEÇÝCÝ ÝPTAL
% clc;
% clear all;
% close all;
ALFA=0.35;

[SEHIR_NO_FCM,X_KONUMU_FCM,Y_KONUMU_FCM]=textread('TSP04.txt','%f %f %f');
data = [X_KONUMU_FCM,Y_KONUMU_FCM];
% CLUSTER_SAYISI=input('Kaç Cluster olsun? 2-10 :');
i=CLUSTER_SAYISI;
colormap(lines(i));
col=lines(i);
% döngü içinde deðiþken oluþturma (['y' int2str(i)])

[center,U,obj_fcn] = fcm(data,i);
% plot(data(:,1), data(:,2),'.');
% hold on;
maxU = max(U);
for j=1:i;
% Find the data points with highest grade of membership in cluster 1
eval(['index' num2str(j) '=find(U(j,:) == maxU);']);
K=1:i;
% Plot the cluster centers
% plot([center([K],1)],[center([K],2)],'*','color','k')
% hold off;
% BAGLANTI_ADAY=find(max(U)<0.5);
eval(['XY' num2str(j) '=center(j,:);']);
% eval(['Y' num2str(j) '=U(j,:);']);
%(['Y' num2str(j)])=U(j,:);
end

switch (CLUSTER_SAYISI)
 % case{1}
 %    line(data(index1,1),data(index1,2),'marker','*','color',col(1,:));
 case{2}
      MX=[XY1;XY2];
      INDEX={index1;index2};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2];
      X_KONUMU2=[XY1(1,1);XY2(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,3)=[];
      SIRA=SON_TUR_CENTER; 
     
          i1=SIRA(1);
          i2=SIRA(2);
          MXx=(MX(i1,1)+MX(i2,1))/2;
          MXy=(MX(i1,2)+MX(i2,2))/2;
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          
          %U1=U(i1,:);
          %U2=U(i2,:);
          U1=U(i1,A);
          U2=U(i2,A);
          %KM=max(U);
          KF=abs(U1-U2);
          % AA=find((KF./KM)<ALFA&(KF./KM)>0);
          % AA=min(KF);
          % BB=find((KF./KM)>-ALFA&(KF./KM)<0);
          
          
          % FARK1=((abs(data(A,1)'-MXx))+(abs(data(A,2)'-MXy)));
          %FARK1=((abs(data(AA,1)'-MXx))+(abs(data(AA,2)'-MXy)));
          %[D1 INDS1]=min(FARK1);
          [D1 INDS1]=min(KF);
          % BAGLA1=A(INDS1);
          BAGLA1=A(INDS1);
          
          U1=U(i1,B);
          U2=U(i2,B);
          KF=abs(U1-U2);
          % FARK2=((abs(data(B,1)'-MXx))+(abs(data(B,2)'-MXy)));
          %FARK2=((abs(data(BB,1)'-MXx))+(abs(data(BB,2)'-MXy)));
          % [D2 INDS2]=min(FARK2);
          [D2 INDS2]=min(KF);
          % BAGLA2=B(INDS2);
          BAGLA2=B(INDS2);
          ADAYLAR=[BAGLA1 BAGLA2]; 
         
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR1=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR1==BAGLA1);
          ROTA1=(circshift(TUR1',numel(TUR1)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR2=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR2==BAGLA2);
          ROTA2=(circshift(TUR2',numel(TUR2)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
      CL=CL1+CL2;
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA1 ROTA2 ROTA1(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR,1), data(ADAYLAR,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       BIRLESIKTUR
%       UZUNLUK
      
      
 case{3}
      MX=[XY1;XY2;XY3];
      INDEX={index1;index2;index3};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,4)=[];
      SIRA=SON_TUR_CENTER;
           
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
                    
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          
          
          U1=U(i1,A);
          U2=U(i2,A);
          KF=abs(U1-U2);
          %KM=max(U);
          %U1=U(i1,A);
          %U2=U(i2,A);
          %UT1=[U1;U2];
          %KM1=max(UT1);
          %KF1=(U1-U2);
          %AA=find((KF1./KM1)<ALFA&(KF1./KM1)>0);
                                      
          %FARK1=((abs(data(AA,1)'-MXx12))+(abs(data(AA,2)'-MXy12)));
          %[D1 INDS1]=min(FARK1);
          [D1 INDS1]=min(KF);
          %BAGLA1=A(AA(INDS1));
          BAGLA1=A(INDS1);
          
          
          U1=U(i1,B);
          U2=U(i2,B);
          KF=abs(U1-U2);
          
          %U1=U(i1,B);
          %U2=U(i2,B);
          %UT1=[U1;U2];
          %KM1=max(UT1);
          %KF1=(U2-U1);
          %BB1=find((KF1./KM1)<ALFA&(KF1./KM1)>0);
                    
          %FARK2=((abs(data(BB1,1)'-MXx12))+(abs(data(BB1,2)'-MXy12)));
          %[D2 INDS2]=min(FARK2);
          [D2 INDS2]=min(KF);
          % BAGLA2=B(BB1(INDS2));
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          
          
          U1=U(i2,B);
          U2=U(i3,B);
          KF=abs(U1-U2);
          %UT1=[U1;U2];
          %KM1=max(UT1);
          %KF1=(U1-U2);
          %BB2=find((KF1./KM1)<ALFA&(KF1./KM1)>0);
          
          %FARK3=((abs(data(BB2,1)'-MXx23))+(abs(data(BB2,2)'-MXy23)));
          %[D3 INDS3]=min(FARK3);
          [D3 INDS3]=min(KF);
          %BAGLA3=B(BB2(INDS3));
          BAGLA3=B(INDS3);
          
          U1=U(i2,C);
          U2=U(i3,C);
          KF=abs(U1-U2);
          %UT1=[U1;U2];
          %KM1=max(UT1);
          %KF1=(U2-U1);
          %CC=find((KF1./KM1)<ALFA&(KF1./KM1)>0);
          
          %FARK4=((abs(data(CC,1)'-MXx23))+(abs(data(CC,2)'-MXy23)));
          %[D4 INDS4]=min(FARK4);
          [D4 INDS4]=min(KF);
          % BAGLA4=C(CC(INDS4));
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
         
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR1=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR1==BAGLA1);
          ROTA1=(circshift(TUR1',numel(TUR1)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR2=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR2==BAGLA2);
          ROTA2=(circshift(TUR2',numel(TUR2)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR3=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR3==BAGLA4);
          ROTA3=(circshift(TUR3',numel(TUR3)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_ILK=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
                
      CL=CL1+CL2+CL3;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA_ILK ROTA3 ROTA_ILK(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       BIRLESIKTUR
%       UZUNLUK
           
case{4}
      MX=[XY1;XY2;XY3;XY4];
      INDEX={index1;index2;index3;index4};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3 4];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1);XY4(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2);XY4(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,5)=[];
      SIRA=SON_TUR_CENTER;
      
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          i4=SIRA(4);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
          
          MXx34=(MX(i3,1)+MX(i4,1))/2;
          MXy34=(MX(i3,2)+MX(i4,2))/2;
                    
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          D=[INDEX{i4}];
                           
          %%% 1. VE 2. SIRA BAÐLANTI
          U1=U(i1,A);
          U2=U(i2,A);
          KF=abs(U1-U2);
          
          % FARK1=((abs(data(A,1)'-MXx12))+(abs(data(A,2)'-MXy12)));
          %[D1 INDS1]=min(FARK1);
          [D1 INDS1]=min(KF);
          BAGLA1=A(INDS1);
          
          U1=U(i1,B);
          U2=U(i2,B);
          KF=abs(U1-U2);
          
          % FARK2=((abs(data(B,1)'-MXx12))+(abs(data(B,2)'-MXy12)));
          % [D2 INDS2]=min(FARK2);
          [D2 INDS2]=min(KF);
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          %%% 2. VE 3. SIRA BAÐLANTI
          U1=U(i2,B);
          U2=U(i3,B);
          KF=abs(U1-U2);
          
          % FARK3=((abs(data(B,1)'-MXx23))+(abs(data(B,2)'-MXy23)));
          %[D3 INDS3]=min(FARK3);
          [D3 INDS3]=min(KF);
          BAGLA3=B(INDS3);
          
          U1=U(i2,C);
          U2=U(i3,C);
          KF=abs(U1-U2);
          
          % FARK4=((abs(data(C,1)'-MXx23))+(abs(data(C,2)'-MXy23)));
          % [D4 INDS4]=min(FARK4);
          [D4 INDS4]=min(KF);
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
          
          %%% 3. VE 4. SIRA BAÐLANTI
          U1=U(i3,C);
          U2=U(i4,C);
          KF=abs(U1-U2);
          
          % FARK5=((abs(data(C,1)'-MXx34))+(abs(data(C,2)'-MXy34)));
          % [D5 INDS5]=min(FARK5);
          [D5 INDS5]=min(KF);
          BAGLA5=C(INDS5);
          
          U1=U(i3,D);
          U2=U(i4,D);
          KF=abs(U1-U2);
          
          % FARK6=((abs(data(D,1)'-MXx34))+(abs(data(D,2)'-MXy34)));
          % [D6 INDS6]=min(FARK6);
          [D6 INDS6]=min(KF);
          BAGLA6=D(INDS6);
          ADAYLAR3=[BAGLA5 BAGLA6];
          
          
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR_A=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR_A==BAGLA1);
          ROTA1=(circshift(TUR_A',numel(TUR_A)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR_B=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR_B==BAGLA2);
          ROTA2=(circshift(TUR_B',numel(TUR_B)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR_C=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR_C==BAGLA4);
          ROTA3=(circshift(TUR_C',numel(TUR_C)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_12_SON=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123=[ROTA_12_SON ROTA3];
          
          
          SEHIR_NO1=D;
          X_KONUMU1=data(D,1);
          Y_KONUMU1=data(D,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL4=calc;
          GBEST4=single(G_izle);
          TUR_D=SEHIR_NO1(SON_TUR);
          SHIFT5=find(TUR_D==BAGLA6);
          ROTA4=(circshift(TUR_D',numel(TUR_D)-SHIFT5+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT6=find(ROTA123==BAGLA5);
          ROTA_123_SON=(circshift(ROTA123',numel(ROTA123)-SHIFT6))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234=[ROTA_123_SON ROTA4];
          
      CL=CL1+CL2+CL3+CL4;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA1234 ROTA1234(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(ADAYLAR3,1), data(ADAYLAR3,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       plot(data(index4,1),data(index4,2),'*','color',col(4,:));
%       BIRLESIKTUR
%       UZUNLUK
           
       
                      
case{5}
      MX=[XY1;XY2;XY3;XY4;XY5];
      INDEX={index1;index2;index3;index4;index5};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3 4 5];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1);XY4(1,1);XY5(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2);XY4(1,2);XY5(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,6)=[];
      SIRA=SON_TUR_CENTER;
      
      
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          i4=SIRA(4);
          i5=SIRA(5);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
          
          MXx34=(MX(i3,1)+MX(i4,1))/2;
          MXy34=(MX(i3,2)+MX(i4,2))/2;
          
          MXx45=(MX(i4,1)+MX(i5,1))/2;
          MXy45=(MX(i4,2)+MX(i5,2))/2;
                    
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          D=[INDEX{i4}];
          E=[INDEX{i5}];
          
          %%% 1. VE 2. SIRA BAÐLANTI
          U1=U(i1,A);
          U2=U(i2,A);
          KF=abs(U1-U2);
          
          %FARK1=((abs(data(A,1)'-MXx12))+(abs(data(A,2)'-MXy12)));
          %[D1 INDS1]=min(FARK1);
          [D1 INDS1]=min(KF);
          BAGLA1=A(INDS1);
          
          U1=U(i1,B);
          U2=U(i2,B);
          KF=abs(U1-U2);
          %FARK2=((abs(data(B,1)'-MXx12))+(abs(data(B,2)'-MXy12)));
          %[D2 INDS2]=min(FARK2);
          [D2 INDS2]=min(KF);
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          %%% 2. VE 3. SIRA BAÐLANTI
          U1=U(i2,B);
          U2=U(i3,B);
          KF=abs(U1-U2);
          
          % FARK3=((abs(data(B,1)'-MXx23))+(abs(data(B,2)'-MXy23)));
          %[D3 INDS3]=min(FARK3);
          [D3 INDS3]=min(KF);
          BAGLA3=B(INDS3);
          
          U1=U(i2,C);
          U2=U(i3,C);
          KF=abs(U1-U2);
          %FARK4=((abs(data(C,1)'-MXx23))+(abs(data(C,2)'-MXy23)));
          %[D4 INDS4]=min(FARK4);
          [D4 INDS4]=min(KF);
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
          
          %%% 3. VE 4. SIRA BAÐLANTI
          U1=U(i3,C);
          U2=U(i4,C);
          KF=abs(U1-U2);
          
          % FARK5=((abs(data(C,1)'-MXx34))+(abs(data(C,2)'-MXy34)));
          % [D5 INDS5]=min(FARK5);
          [D5 INDS5]=min(KF);
          BAGLA5=C(INDS5);
          
          U1=U(i3,D);
          U2=U(i4,D);
          KF=abs(U1-U2);
          
          % FARK6=((abs(data(D,1)'-MXx34))+(abs(data(D,2)'-MXy34)));
          % [D6 INDS6]=min(FARK6);
          [D6 INDS6]=min(KF);
          BAGLA6=D(INDS6);
          ADAYLAR3=[BAGLA5 BAGLA6];
          
          %%% 4. VE 5. SIRA BAÐLANTI
          U1=U(i4,D);
          U2=U(i5,D);
          KF=abs(U1-U2);
          
          % FARK7=((abs(data(D,1)'-MXx45))+(abs(data(D,2)'-MXy45)));
          %[D7 INDS7]=min(FARK7);
          [D7 INDS7]=min(KF);
          BAGLA7=D(INDS7);
          
          U1=U(i4,E);
          U2=U(i5,E);
          KF=abs(U1-U2);
          
          % FARK8=((abs(data(E,1)'-MXx45))+(abs(data(E,2)'-MXy45)));
          % [D8 INDS8]=min(FARK8);
          [D8 INDS8]=min(KF);
          BAGLA8=E(INDS8);
          ADAYLAR4=[BAGLA7 BAGLA8];
          
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR_A=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR_A==BAGLA1);
          ROTA1=(circshift(TUR_A',numel(TUR_A)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR_B=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR_B==BAGLA2);
          ROTA2=(circshift(TUR_B',numel(TUR_B)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR_C=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR_C==BAGLA4);
          ROTA3=(circshift(TUR_C',numel(TUR_C)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_12_SON=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123=[ROTA_12_SON ROTA3];
          
          
          SEHIR_NO1=D;
          X_KONUMU1=data(D,1);
          Y_KONUMU1=data(D,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL4=calc;
          GBEST4=single(G_izle);
          TUR_D=SEHIR_NO1(SON_TUR);
          SHIFT5=find(TUR_D==BAGLA6);
          ROTA4=(circshift(TUR_D',numel(TUR_D)-SHIFT5+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT6=find(ROTA123==BAGLA5);
          ROTA_123_SON=(circshift(ROTA123',numel(ROTA123)-SHIFT6))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234=[ROTA_123_SON ROTA4];
          
          SEHIR_NO1=E;
          X_KONUMU1=data(E,1);
          Y_KONUMU1=data(E,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL5=calc;
          GBEST5=single(G_izle);
          TUR_E=SEHIR_NO1(SON_TUR);
          SHIFT7=find(TUR_E==BAGLA8);
          ROTA5=(circshift(TUR_E',numel(TUR_E)-SHIFT7+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT8=find(ROTA1234==BAGLA7);
          ROTA_1234_SON=(circshift(ROTA1234',numel(ROTA1234)-SHIFT8))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345=[ROTA_1234_SON ROTA5];
          
      CL=CL1+CL2+CL3+CL4+CL5;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA12345 ROTA12345(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(ADAYLAR3,1), data(ADAYLAR3,2),'s');
%       plot(data(ADAYLAR4,1), data(ADAYLAR4,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       plot(data(index4,1),data(index4,2),'*','color',col(4,:));
%       plot(data(index5,1),data(index5,2),'*','color',col(5,:));
%       BIRLESIKTUR
%       UZUNLUK
    
      
case{6}
      MX=[XY1;XY2;XY3;XY4;XY5;XY6];
      INDEX={index1;index2;index3;index4;index5;index6};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3 4 5 6];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1);XY4(1,1);XY5(1,1);XY6(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2);XY4(1,2);XY5(1,2);XY6(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,7)=[];
      SIRA=SON_TUR_CENTER;
      
      
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          i4=SIRA(4);
          i5=SIRA(5);
          i6=SIRA(6);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
          
          MXx34=(MX(i3,1)+MX(i4,1))/2;
          MXy34=(MX(i3,2)+MX(i4,2))/2;
          
          MXx45=(MX(i4,1)+MX(i5,1))/2;
          MXy45=(MX(i4,2)+MX(i5,2))/2;
          
          MXx56=(MX(i5,1)+MX(i6,1))/2;
          MXy56=(MX(i5,2)+MX(i6,2))/2;
                    
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          D=[INDEX{i4}];
          E=[INDEX{i5}];
          F=[INDEX{i6}];
          
          %%% 1. VE 2. SIRA BAÐLANTI
          FARK1=((abs(data(A,1)'-MXx12))+(abs(data(A,2)'-MXy12)));
          [D1 INDS1]=min(FARK1);
          BAGLA1=A(INDS1);
          FARK2=((abs(data(B,1)'-MXx12))+(abs(data(B,2)'-MXy12)));
          [D2 INDS2]=min(FARK2);
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          %%% 2. VE 3. SIRA BAÐLANTI
          FARK3=((abs(data(B,1)'-MXx23))+(abs(data(B,2)'-MXy23)));
          [D3 INDS3]=min(FARK3);
          BAGLA3=B(INDS3);
          FARK4=((abs(data(C,1)'-MXx23))+(abs(data(C,2)'-MXy23)));
          [D4 INDS4]=min(FARK4);
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
          
          %%% 3. VE 4. SIRA BAÐLANTI
          FARK5=((abs(data(C,1)'-MXx34))+(abs(data(C,2)'-MXy34)));
          [D5 INDS5]=min(FARK5);
          BAGLA5=C(INDS5);
          FARK6=((abs(data(D,1)'-MXx34))+(abs(data(D,2)'-MXy34)));
          [D6 INDS6]=min(FARK6);
          BAGLA6=D(INDS6);
          ADAYLAR3=[BAGLA5 BAGLA6];
          
          %%% 4. VE 5. SIRA BAÐLANTI
          FARK7=((abs(data(D,1)'-MXx45))+(abs(data(D,2)'-MXy45)));
          [D7 INDS7]=min(FARK7);
          BAGLA7=D(INDS7);
          FARK8=((abs(data(E,1)'-MXx45))+(abs(data(E,2)'-MXy45)));
          [D8 INDS8]=min(FARK8);
          BAGLA8=E(INDS8);
          ADAYLAR4=[BAGLA7 BAGLA8];
          
          %%% 5. VE 6. SIRA BAÐLANTI
          FARK9=((abs(data(E,1)'-MXx56))+(abs(data(E,2)'-MXy56)));
          [D9 INDS9]=min(FARK9);
          BAGLA9=E(INDS9);
          FARK10=((abs(data(F,1)'-MXx56))+(abs(data(F,2)'-MXy56)));
          [D10 INDS10]=min(FARK10);
          BAGLA10=F(INDS10);
          ADAYLAR5=[BAGLA9 BAGLA10];
          
          
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR_A=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR_A==BAGLA1);
          ROTA1=(circshift(TUR_A',numel(TUR_A)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR_B=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR_B==BAGLA2);
          ROTA2=(circshift(TUR_B',numel(TUR_B)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR_C=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR_C==BAGLA4);
          ROTA3=(circshift(TUR_C',numel(TUR_C)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_12_SON=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123=[ROTA_12_SON ROTA3];
          
          
          SEHIR_NO1=D;
          X_KONUMU1=data(D,1);
          Y_KONUMU1=data(D,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL4=calc;
          GBEST4=single(G_izle);
          TUR_D=SEHIR_NO1(SON_TUR);
          SHIFT5=find(TUR_D==BAGLA6);
          ROTA4=(circshift(TUR_D',numel(TUR_D)-SHIFT5+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT6=find(ROTA123==BAGLA5);
          ROTA_123_SON=(circshift(ROTA123',numel(ROTA123)-SHIFT6))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234=[ROTA_123_SON ROTA4];
          
          SEHIR_NO1=E;
          X_KONUMU1=data(E,1);
          Y_KONUMU1=data(E,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL5=calc;
          GBEST5=single(G_izle);
          TUR_E=SEHIR_NO1(SON_TUR);
          SHIFT7=find(TUR_E==BAGLA8);
          ROTA5=(circshift(TUR_E',numel(TUR_E)-SHIFT7+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT8=find(ROTA1234==BAGLA7);
          ROTA_1234_SON=(circshift(ROTA1234',numel(ROTA1234)-SHIFT8))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345=[ROTA_1234_SON ROTA5];
          
          SEHIR_NO1=F;
          X_KONUMU1=data(F,1);
          Y_KONUMU1=data(F,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL6=calc;
          GBEST6=single(G_izle);
          TUR_F=SEHIR_NO1(SON_TUR);
          SHIFT9=find(TUR_F==BAGLA10);
          ROTA6=(circshift(TUR_F',numel(TUR_F)-SHIFT9+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT10=find(ROTA12345==BAGLA9);
          ROTA_12345_SON=(circshift(ROTA12345',numel(ROTA12345)-SHIFT10))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123456=[ROTA_12345_SON ROTA6];
          
      CL=CL1+CL2+CL3+CL4+CL5;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA123456 ROTA123456(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(ADAYLAR3,1), data(ADAYLAR3,2),'s');
%       plot(data(ADAYLAR4,1), data(ADAYLAR4,2),'s');
%       plot(data(ADAYLAR5,1), data(ADAYLAR5,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       plot(data(index4,1),data(index4,2),'*','color',col(4,:));
%       plot(data(index5,1),data(index5,2),'*','color',col(5,:));
%       plot(data(index6,1),data(index6,2),'*','color',col(6,:));
%       BIRLESIKTUR
%       UZUNLUK

      
case{7}
      MX=[XY1;XY2;XY3;XY4;XY5;XY6;XY7];
      INDEX={index1;index2;index3;index4;index5;index6;index7};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3 4 5 6 7];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1);XY4(1,1);XY5(1,1);XY6(1,1);XY7(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2);XY4(1,2);XY5(1,2);XY6(1,2);XY7(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,8)=[];
      SIRA=SON_TUR_CENTER;
      
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          i4=SIRA(4);
          i5=SIRA(5);
          i6=SIRA(6);
          i7=SIRA(7);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
          
          MXx34=(MX(i3,1)+MX(i4,1))/2;
          MXy34=(MX(i3,2)+MX(i4,2))/2;
          
          MXx45=(MX(i4,1)+MX(i5,1))/2;
          MXy45=(MX(i4,2)+MX(i5,2))/2;
          
          MXx56=(MX(i5,1)+MX(i6,1))/2;
          MXy56=(MX(i5,2)+MX(i6,2))/2;
          
          MXx67=(MX(i6,1)+MX(i7,1))/2;
          MXy67=(MX(i6,2)+MX(i7,2))/2;
                    
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          D=[INDEX{i4}];
          E=[INDEX{i5}];
          F=[INDEX{i6}];
          G=[INDEX{i7}];
          
          %%% 1. VE 2. SIRA BAÐLANTI
          FARK1=((abs(data(A,1)'-MXx12))+(abs(data(A,2)'-MXy12)));
          [D1 INDS1]=min(FARK1);
          BAGLA1=A(INDS1);
          FARK2=((abs(data(B,1)'-MXx12))+(abs(data(B,2)'-MXy12)));
          [D2 INDS2]=min(FARK2);
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          %%% 2. VE 3. SIRA BAÐLANTI
          FARK3=((abs(data(B,1)'-MXx23))+(abs(data(B,2)'-MXy23)));
          [D3 INDS3]=min(FARK3);
          BAGLA3=B(INDS3);
          FARK4=((abs(data(C,1)'-MXx23))+(abs(data(C,2)'-MXy23)));
          [D4 INDS4]=min(FARK4);
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
          
          %%% 3. VE 4. SIRA BAÐLANTI
          FARK5=((abs(data(C,1)'-MXx34))+(abs(data(C,2)'-MXy34)));
          [D5 INDS5]=min(FARK5);
          BAGLA5=C(INDS5);
          FARK6=((abs(data(D,1)'-MXx34))+(abs(data(D,2)'-MXy34)));
          [D6 INDS6]=min(FARK6);
          BAGLA6=D(INDS6);
          ADAYLAR3=[BAGLA5 BAGLA6];
          
          %%% 4. VE 5. SIRA BAÐLANTI
          FARK7=((abs(data(D,1)'-MXx45))+(abs(data(D,2)'-MXy45)));
          [D7 INDS7]=min(FARK7);
          BAGLA7=D(INDS7);
          FARK8=((abs(data(E,1)'-MXx45))+(abs(data(E,2)'-MXy45)));
          [D8 INDS8]=min(FARK8);
          BAGLA8=E(INDS8);
          ADAYLAR4=[BAGLA7 BAGLA8];
          
          %%% 5. VE 6. SIRA BAÐLANTI
          FARK9=((abs(data(E,1)'-MXx56))+(abs(data(E,2)'-MXy56)));
          [D9 INDS9]=min(FARK9);
          BAGLA9=E(INDS9);
          FARK10=((abs(data(F,1)'-MXx56))+(abs(data(F,2)'-MXy56)));
          [D10 INDS10]=min(FARK10);
          BAGLA10=F(INDS10);
          ADAYLAR5=[BAGLA9 BAGLA10];
          
          %%% 6. VE 7. SIRA BAÐLANTI
          FARK11=((abs(data(F,1)'-MXx67))+(abs(data(F,2)'-MXy67)));
          [D11 INDS11]=min(FARK11);
          BAGLA11=F(INDS11);
          FARK12=((abs(data(G,1)'-MXx67))+(abs(data(G,2)'-MXy67)));
          [D12 INDS12]=min(FARK12);
          BAGLA12=G(INDS12);
          ADAYLAR6=[BAGLA11 BAGLA12];
          
          
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR_A=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR_A==BAGLA1);
          ROTA1=(circshift(TUR_A',numel(TUR_A)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR_B=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR_B==BAGLA2);
          ROTA2=(circshift(TUR_B',numel(TUR_B)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR_C=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR_C==BAGLA4);
          ROTA3=(circshift(TUR_C',numel(TUR_C)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_12_SON=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123=[ROTA_12_SON ROTA3];
          
          
          SEHIR_NO1=D;
          X_KONUMU1=data(D,1);
          Y_KONUMU1=data(D,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL4=calc;
          GBEST4=single(G_izle);
          TUR_D=SEHIR_NO1(SON_TUR);
          SHIFT5=find(TUR_D==BAGLA6);
          ROTA4=(circshift(TUR_D',numel(TUR_D)-SHIFT5+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT6=find(ROTA123==BAGLA5);
          ROTA_123_SON=(circshift(ROTA123',numel(ROTA123)-SHIFT6))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234=[ROTA_123_SON ROTA4];
          
          SEHIR_NO1=E;
          X_KONUMU1=data(E,1);
          Y_KONUMU1=data(E,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL5=calc;
          GBEST5=single(G_izle);
          TUR_E=SEHIR_NO1(SON_TUR);
          SHIFT7=find(TUR_E==BAGLA8);
          ROTA5=(circshift(TUR_E',numel(TUR_E)-SHIFT7+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT8=find(ROTA1234==BAGLA7);
          ROTA_1234_SON=(circshift(ROTA1234',numel(ROTA1234)-SHIFT8))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345=[ROTA_1234_SON ROTA5];
          
          SEHIR_NO1=F;
          X_KONUMU1=data(F,1);
          Y_KONUMU1=data(F,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL6=calc;
          GBEST6=single(G_izle);
          TUR_F=SEHIR_NO1(SON_TUR);
          SHIFT9=find(TUR_F==BAGLA10);
          ROTA6=(circshift(TUR_F',numel(TUR_F)-SHIFT9+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT10=find(ROTA12345==BAGLA9);
          ROTA_12345_SON=(circshift(ROTA12345',numel(ROTA12345)-SHIFT10))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123456=[ROTA_12345_SON ROTA6];
          
          SEHIR_NO1=G;
          X_KONUMU1=data(G,1);
          Y_KONUMU1=data(G,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL7=calc;
          GBEST7=single(G_izle);
          TUR_G=SEHIR_NO1(SON_TUR);
          SHIFT11=find(TUR_G==BAGLA12);
          ROTA7=(circshift(TUR_G',numel(TUR_G)-SHIFT11+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT12=find(ROTA123456==BAGLA11);
          ROTA_123456_SON=(circshift(ROTA123456',numel(ROTA123456)-SHIFT12))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234567=[ROTA_123456_SON ROTA7];
          
      CL=CL1+CL2+CL3+CL4+CL5+CL6+CL7;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA1234567 ROTA1234567(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(ADAYLAR3,1), data(ADAYLAR3,2),'s');
%       plot(data(ADAYLAR4,1), data(ADAYLAR4,2),'s');
%       plot(data(ADAYLAR5,1), data(ADAYLAR5,2),'s');
%       plot(data(ADAYLAR6,1), data(ADAYLAR6,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       plot(data(index4,1),data(index4,2),'*','color',col(4,:));
%       plot(data(index5,1),data(index5,2),'*','color',col(5,:));
%       plot(data(index6,1),data(index6,2),'*','color',col(6,:));
%       plot(data(index7,1),data(index7,2),'*','color',col(7,:));
%       BIRLESIKTUR
%       UZUNLUK
         
      
case{8}
      MX=[XY1;XY2;XY3;XY4;XY5;XY6;XY7;XY8];
      INDEX={index1;index2;index3;index4;index5;index6;index7;index8};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3 4 5 6 7 8];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1);XY4(1,1);XY5(1,1);XY6(1,1);XY7(1,1);XY8(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2);XY4(1,2);XY5(1,2);XY6(1,2);XY7(1,2);XY8(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,9)=[];
      SIRA=SON_TUR_CENTER;
      
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          i4=SIRA(4);
          i5=SIRA(5);
          i6=SIRA(6);
          i7=SIRA(7);
          i8=SIRA(8);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
          
          MXx34=(MX(i3,1)+MX(i4,1))/2;
          MXy34=(MX(i3,2)+MX(i4,2))/2;
          
          MXx45=(MX(i4,1)+MX(i5,1))/2;
          MXy45=(MX(i4,2)+MX(i5,2))/2;
          
          MXx56=(MX(i5,1)+MX(i6,1))/2;
          MXy56=(MX(i5,2)+MX(i6,2))/2;
          
          MXx67=(MX(i6,1)+MX(i7,1))/2;
          MXy67=(MX(i6,2)+MX(i7,2))/2;
          
          MXx78=(MX(i7,1)+MX(i8,1))/2;
          MXy78=(MX(i7,2)+MX(i8,2))/2;
                    
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          D=[INDEX{i4}];
          E=[INDEX{i5}];
          F=[INDEX{i6}];
          G=[INDEX{i7}];
          H=[INDEX{i8}];
          
          %%% 1. VE 2. SIRA BAÐLANTI
          FARK1=((abs(data(A,1)'-MXx12))+(abs(data(A,2)'-MXy12)));
          [D1 INDS1]=min(FARK1);
          BAGLA1=A(INDS1);
          FARK2=((abs(data(B,1)'-MXx12))+(abs(data(B,2)'-MXy12)));
          [D2 INDS2]=min(FARK2);
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          %%% 2. VE 3. SIRA BAÐLANTI
          FARK3=((abs(data(B,1)'-MXx23))+(abs(data(B,2)'-MXy23)));
          [D3 INDS3]=min(FARK3);
          BAGLA3=B(INDS3);
          FARK4=((abs(data(C,1)'-MXx23))+(abs(data(C,2)'-MXy23)));
          [D4 INDS4]=min(FARK4);
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
          
          %%% 3. VE 4. SIRA BAÐLANTI
          FARK5=((abs(data(C,1)'-MXx34))+(abs(data(C,2)'-MXy34)));
          [D5 INDS5]=min(FARK5);
          BAGLA5=C(INDS5);
          FARK6=((abs(data(D,1)'-MXx34))+(abs(data(D,2)'-MXy34)));
          [D6 INDS6]=min(FARK6);
          BAGLA6=D(INDS6);
          ADAYLAR3=[BAGLA5 BAGLA6];
          
          %%% 4. VE 5. SIRA BAÐLANTI
          FARK7=((abs(data(D,1)'-MXx45))+(abs(data(D,2)'-MXy45)));
          [D7 INDS7]=min(FARK7);
          BAGLA7=D(INDS7);
          FARK8=((abs(data(E,1)'-MXx45))+(abs(data(E,2)'-MXy45)));
          [D8 INDS8]=min(FARK8);
          BAGLA8=E(INDS8);
          ADAYLAR4=[BAGLA7 BAGLA8];
          
          %%% 5. VE 6. SIRA BAÐLANTI
          FARK9=((abs(data(E,1)'-MXx56))+(abs(data(E,2)'-MXy56)));
          [D9 INDS9]=min(FARK9);
          BAGLA9=E(INDS9);
          FARK10=((abs(data(F,1)'-MXx56))+(abs(data(F,2)'-MXy56)));
          [D10 INDS10]=min(FARK10);
          BAGLA10=F(INDS10);
          ADAYLAR5=[BAGLA9 BAGLA10];
          
          %%% 6. VE 7. SIRA BAÐLANTI
          FARK11=((abs(data(F,1)'-MXx67))+(abs(data(F,2)'-MXy67)));
          [D11 INDS11]=min(FARK11);
          BAGLA11=F(INDS11);
          FARK12=((abs(data(G,1)'-MXx67))+(abs(data(G,2)'-MXy67)));
          [D12 INDS12]=min(FARK12);
          BAGLA12=G(INDS12);
          ADAYLAR6=[BAGLA11 BAGLA12];
          
          %%% 7. VE 8. SIRA BAÐLANTI
          FARK13=((abs(data(G,1)'-MXx78))+(abs(data(G,2)'-MXy78)));
          [D13 INDS13]=min(FARK13);
          BAGLA13=G(INDS13);
          FARK14=((abs(data(H,1)'-MXx78))+(abs(data(H,2)'-MXy78)));
          [D14 INDS14]=min(FARK14);
          BAGLA14=H(INDS14);
          ADAYLAR7=[BAGLA13 BAGLA14];
          
          
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR_A=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR_A==BAGLA1);
          ROTA1=(circshift(TUR_A',numel(TUR_A)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR_B=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR_B==BAGLA2);
          ROTA2=(circshift(TUR_B',numel(TUR_B)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR_C=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR_C==BAGLA4);
          ROTA3=(circshift(TUR_C',numel(TUR_C)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_12_SON=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123=[ROTA_12_SON ROTA3];
          
          
          SEHIR_NO1=D;
          X_KONUMU1=data(D,1);
          Y_KONUMU1=data(D,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL4=calc;
          GBEST4=single(G_izle);
          TUR_D=SEHIR_NO1(SON_TUR);
          SHIFT5=find(TUR_D==BAGLA6);
          ROTA4=(circshift(TUR_D',numel(TUR_D)-SHIFT5+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT6=find(ROTA123==BAGLA5);
          ROTA_123_SON=(circshift(ROTA123',numel(ROTA123)-SHIFT6))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234=[ROTA_123_SON ROTA4];
          
          SEHIR_NO1=E;
          X_KONUMU1=data(E,1);
          Y_KONUMU1=data(E,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL5=calc;
          GBEST5=single(G_izle);
          TUR_E=SEHIR_NO1(SON_TUR);
          SHIFT7=find(TUR_E==BAGLA8);
          ROTA5=(circshift(TUR_E',numel(TUR_E)-SHIFT7+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT8=find(ROTA1234==BAGLA7);
          ROTA_1234_SON=(circshift(ROTA1234',numel(ROTA1234)-SHIFT8))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345=[ROTA_1234_SON ROTA5];
          
          SEHIR_NO1=F;
          X_KONUMU1=data(F,1);
          Y_KONUMU1=data(F,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL6=calc;
          GBEST6=single(G_izle);
          TUR_F=SEHIR_NO1(SON_TUR);
          SHIFT9=find(TUR_F==BAGLA10);
          ROTA6=(circshift(TUR_F',numel(TUR_F)-SHIFT9+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT10=find(ROTA12345==BAGLA9);
          ROTA_12345_SON=(circshift(ROTA12345',numel(ROTA12345)-SHIFT10))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123456=[ROTA_12345_SON ROTA6];
          
          SEHIR_NO1=G;
          X_KONUMU1=data(G,1);
          Y_KONUMU1=data(G,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL7=calc;
          GBEST7=single(G_izle);
          TUR_G=SEHIR_NO1(SON_TUR);
          SHIFT11=find(TUR_G==BAGLA12);
          ROTA7=(circshift(TUR_G',numel(TUR_G)-SHIFT11+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT12=find(ROTA123456==BAGLA11);
          ROTA_123456_SON=(circshift(ROTA123456',numel(ROTA123456)-SHIFT12))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234567=[ROTA_123456_SON ROTA7];
          
          SEHIR_NO1=H;
          X_KONUMU1=data(H,1);
          Y_KONUMU1=data(H,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL8=calc;
          GBEST8=single(G_izle);
          TUR_H=SEHIR_NO1(SON_TUR);
          SHIFT13=find(TUR_H==BAGLA14);
          ROTA8=(circshift(TUR_H',numel(TUR_H)-SHIFT13+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT14=find(ROTA1234567==BAGLA13);
          ROTA_1234567_SON=(circshift(ROTA1234567',numel(ROTA1234567)-SHIFT14))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345678=[ROTA_1234567_SON ROTA8];
          
          
      CL=CL1+CL2+CL3+CL4+CL5+CL6+CL7+CL8;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA12345678 ROTA12345678(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(ADAYLAR3,1), data(ADAYLAR3,2),'s');
%       plot(data(ADAYLAR4,1), data(ADAYLAR4,2),'s');
%       plot(data(ADAYLAR5,1), data(ADAYLAR5,2),'s');
%       plot(data(ADAYLAR6,1), data(ADAYLAR6,2),'s');
%       plot(data(ADAYLAR7,1), data(ADAYLAR7,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       plot(data(index4,1),data(index4,2),'*','color',col(4,:));
%       plot(data(index5,1),data(index5,2),'*','color',col(5,:));
%       plot(data(index6,1),data(index6,2),'*','color',col(6,:));
%       plot(data(index7,1),data(index7,2),'*','color',col(7,:));
%       plot(data(index8,1),data(index8,2),'*','color',col(8,:));
%       BIRLESIKTUR
%       UZUNLUK
      
             
case{9}
      MX=[XY1;XY2;XY3;XY4;XY5;XY6;XY7;XY8;XY9];
      INDEX={index1;index2;index3;index4;index5;index6;index7;index8;index9};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3 4 5 6 7 8 9];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1);XY4(1,1);XY5(1,1);XY6(1,1);XY7(1,1);XY8(1,1);XY9(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2);XY4(1,2);XY5(1,2);XY6(1,2);XY7(1,2);XY8(1,2);XY9(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,10)=[];
      SIRA=SON_TUR_CENTER;
      
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          i4=SIRA(4);
          i5=SIRA(5);
          i6=SIRA(6);
          i7=SIRA(7);
          i8=SIRA(8);
          i9=SIRA(9);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
          
          MXx34=(MX(i3,1)+MX(i4,1))/2;
          MXy34=(MX(i3,2)+MX(i4,2))/2;
          
          MXx45=(MX(i4,1)+MX(i5,1))/2;
          MXy45=(MX(i4,2)+MX(i5,2))/2;
          
          MXx56=(MX(i5,1)+MX(i6,1))/2;
          MXy56=(MX(i5,2)+MX(i6,2))/2;
          
          MXx67=(MX(i6,1)+MX(i7,1))/2;
          MXy67=(MX(i6,2)+MX(i7,2))/2;
          
          MXx78=(MX(i7,1)+MX(i8,1))/2;
          MXy78=(MX(i7,2)+MX(i8,2))/2;
          
          MXx89=(MX(i8,1)+MX(i9,1))/2;
          MXy89=(MX(i8,2)+MX(i9,2))/2;
          
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          D=[INDEX{i4}];
          E=[INDEX{i5}];
          F=[INDEX{i6}];
          G=[INDEX{i7}];
          H=[INDEX{i8}];
          I=[INDEX{i9}];
          
          %%% 1. VE 2. SIRA BAÐLANTI
          FARK1=((abs(data(A,1)'-MXx12))+(abs(data(A,2)'-MXy12)));
          [D1 INDS1]=min(FARK1);
          BAGLA1=A(INDS1);
          FARK2=((abs(data(B,1)'-MXx12))+(abs(data(B,2)'-MXy12)));
          [D2 INDS2]=min(FARK2);
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          %%% 2. VE 3. SIRA BAÐLANTI
          FARK3=((abs(data(B,1)'-MXx23))+(abs(data(B,2)'-MXy23)));
          [D3 INDS3]=min(FARK3);
          BAGLA3=B(INDS3);
          FARK4=((abs(data(C,1)'-MXx23))+(abs(data(C,2)'-MXy23)));
          [D4 INDS4]=min(FARK4);
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
          
          %%% 3. VE 4. SIRA BAÐLANTI
          FARK5=((abs(data(C,1)'-MXx34))+(abs(data(C,2)'-MXy34)));
          [D5 INDS5]=min(FARK5);
          BAGLA5=C(INDS5);
          FARK6=((abs(data(D,1)'-MXx34))+(abs(data(D,2)'-MXy34)));
          [D6 INDS6]=min(FARK6);
          BAGLA6=D(INDS6);
          ADAYLAR3=[BAGLA5 BAGLA6];
          
          %%% 4. VE 5. SIRA BAÐLANTI
          FARK7=((abs(data(D,1)'-MXx45))+(abs(data(D,2)'-MXy45)));
          [D7 INDS7]=min(FARK7);
          BAGLA7=D(INDS7);
          FARK8=((abs(data(E,1)'-MXx45))+(abs(data(E,2)'-MXy45)));
          [D8 INDS8]=min(FARK8);
          BAGLA8=E(INDS8);
          ADAYLAR4=[BAGLA7 BAGLA8];
          
          %%% 5. VE 6. SIRA BAÐLANTI
          FARK9=((abs(data(E,1)'-MXx56))+(abs(data(E,2)'-MXy56)));
          [D9 INDS9]=min(FARK9);
          BAGLA9=E(INDS9);
          FARK10=((abs(data(F,1)'-MXx56))+(abs(data(F,2)'-MXy56)));
          [D10 INDS10]=min(FARK10);
          BAGLA10=F(INDS10);
          ADAYLAR5=[BAGLA9 BAGLA10];
          
          %%% 6. VE 7. SIRA BAÐLANTI
          FARK11=((abs(data(F,1)'-MXx67))+(abs(data(F,2)'-MXy67)));
          [D11 INDS11]=min(FARK11);
          BAGLA11=F(INDS11);
          FARK12=((abs(data(G,1)'-MXx67))+(abs(data(G,2)'-MXy67)));
          [D12 INDS12]=min(FARK12);
          BAGLA12=G(INDS12);
          ADAYLAR6=[BAGLA11 BAGLA12];
          
          %%% 7. VE 8. SIRA BAÐLANTI
          FARK13=((abs(data(G,1)'-MXx78))+(abs(data(G,2)'-MXy78)));
          [D13 INDS13]=min(FARK13);
          BAGLA13=G(INDS13);
          FARK14=((abs(data(H,1)'-MXx78))+(abs(data(H,2)'-MXy78)));
          [D14 INDS14]=min(FARK14);
          BAGLA14=H(INDS14);
          ADAYLAR7=[BAGLA13 BAGLA14];
          
          %%% 8. VE 9. SIRA BAÐLANTI
          FARK15=((abs(data(H,1)'-MXx89))+(abs(data(H,2)'-MXy89)));
          [D15 INDS15]=min(FARK15);
          BAGLA15=H(INDS15);
          FARK16=((abs(data(I,1)'-MXx89))+(abs(data(I,2)'-MXy89)));
          [D16 INDS16]=min(FARK16);
          BAGLA16=I(INDS16);
          ADAYLAR8=[BAGLA15 BAGLA16];
          
          
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR_A=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR_A==BAGLA1);
          ROTA1=(circshift(TUR_A',numel(TUR_A)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR_B=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR_B==BAGLA2);
          ROTA2=(circshift(TUR_B',numel(TUR_B)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR_C=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR_C==BAGLA4);
          ROTA3=(circshift(TUR_C',numel(TUR_C)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_12_SON=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123=[ROTA_12_SON ROTA3];
          
          
          SEHIR_NO1=D;
          X_KONUMU1=data(D,1);
          Y_KONUMU1=data(D,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL4=calc;
          GBEST4=single(G_izle);
          TUR_D=SEHIR_NO1(SON_TUR);
          SHIFT5=find(TUR_D==BAGLA6);
          ROTA4=(circshift(TUR_D',numel(TUR_D)-SHIFT5+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT6=find(ROTA123==BAGLA5);
          ROTA_123_SON=(circshift(ROTA123',numel(ROTA123)-SHIFT6))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234=[ROTA_123_SON ROTA4];
          
          SEHIR_NO1=E;
          X_KONUMU1=data(E,1);
          Y_KONUMU1=data(E,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL5=calc;
          GBEST5=single(G_izle);
          TUR_E=SEHIR_NO1(SON_TUR);
          SHIFT7=find(TUR_E==BAGLA8);
          ROTA5=(circshift(TUR_E',numel(TUR_E)-SHIFT7+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT8=find(ROTA1234==BAGLA7);
          ROTA_1234_SON=(circshift(ROTA1234',numel(ROTA1234)-SHIFT8))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345=[ROTA_1234_SON ROTA5];
          
          SEHIR_NO1=F;
          X_KONUMU1=data(F,1);
          Y_KONUMU1=data(F,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL6=calc;
          GBEST6=single(G_izle);
          TUR_F=SEHIR_NO1(SON_TUR);
          SHIFT9=find(TUR_F==BAGLA10);
          ROTA6=(circshift(TUR_F',numel(TUR_F)-SHIFT9+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT10=find(ROTA12345==BAGLA9);
          ROTA_12345_SON=(circshift(ROTA12345',numel(ROTA12345)-SHIFT10))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123456=[ROTA_12345_SON ROTA6];
          
          SEHIR_NO1=G;
          X_KONUMU1=data(G,1);
          Y_KONUMU1=data(G,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL7=calc;
          GBEST7=single(G_izle);
          TUR_G=SEHIR_NO1(SON_TUR);
          SHIFT11=find(TUR_G==BAGLA12);
          ROTA7=(circshift(TUR_G',numel(TUR_G)-SHIFT11+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT12=find(ROTA123456==BAGLA11);
          ROTA_123456_SON=(circshift(ROTA123456',numel(ROTA123456)-SHIFT12))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234567=[ROTA_123456_SON ROTA7];
          
          SEHIR_NO1=H;
          X_KONUMU1=data(H,1);
          Y_KONUMU1=data(H,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL8=calc;
          GBEST8=single(G_izle);
          TUR_H=SEHIR_NO1(SON_TUR);
          SHIFT13=find(TUR_H==BAGLA14);
          ROTA8=(circshift(TUR_H',numel(TUR_H)-SHIFT13+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT14=find(ROTA1234567==BAGLA13);
          ROTA_1234567_SON=(circshift(ROTA1234567',numel(ROTA1234567)-SHIFT14))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345678=[ROTA_1234567_SON ROTA8];
          
          SEHIR_NO1=I;
          X_KONUMU1=data(I,1);
          Y_KONUMU1=data(I,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL9=calc;
          GBEST9=single(G_izle);
          TUR_I=SEHIR_NO1(SON_TUR);
          SHIFT15=find(TUR_I==BAGLA16);
          ROTA9=(circshift(TUR_I',numel(TUR_I)-SHIFT15+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT16=find(ROTA12345678==BAGLA15);
          ROTA_12345678_SON=(circshift(ROTA12345678',numel(ROTA12345678)-SHIFT16))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123456789=[ROTA_12345678_SON ROTA9];
          
          
      CL=CL1+CL2+CL3+CL4+CL5+CL6+CL7+CL8+CL9;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA123456789 ROTA123456789(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(ADAYLAR3,1), data(ADAYLAR3,2),'s');
%       plot(data(ADAYLAR4,1), data(ADAYLAR4,2),'s');
%       plot(data(ADAYLAR5,1), data(ADAYLAR5,2),'s');
%       plot(data(ADAYLAR6,1), data(ADAYLAR6,2),'s');
%       plot(data(ADAYLAR7,1), data(ADAYLAR7,2),'s');
%       plot(data(ADAYLAR8,1), data(ADAYLAR8,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       plot(data(index4,1),data(index4,2),'*','color',col(4,:));
%       plot(data(index5,1),data(index5,2),'*','color',col(5,:));
%       plot(data(index6,1),data(index6,2),'*','color',col(6,:));
%       plot(data(index7,1),data(index7,2),'*','color',col(7,:));
%       plot(data(index8,1),data(index8,2),'*','color',col(8,:));
%       plot(data(index9,1),data(index9,2),'*','color',col(9,:));
%       BIRLESIKTUR
%       UZUNLUK
      
          
case{10}
      MX=[XY1;XY2;XY3;XY4;XY5;XY6;XY7;XY8;XY9;XY10];
      INDEX={index1;index2;index3;index4;index5;index6;index7;index8;index9;index10};
      % CLUSTER BAÐLAMA SIRASI
      SEHIR_NO2=[1 2 3 4 5 6 7 8 9 10];
      X_KONUMU2=[XY1(1,1);XY2(1,1);XY3(1,1);XY4(1,1);XY5(1,1);XY6(1,1);XY7(1,1);XY8(1,1);XY9(1,1);XY10(1,1)];
      Y_KONUMU2=[XY1(1,2);XY2(1,2);XY3(1,2);XY4(1,2);XY5(1,2);XY6(1,2);XY7(1,2);XY8(1,2);XY9(1,2);XY10(1,2)];
      [SON_TUR_CENTER]=TSPorjFUN_CLUSTER(SEHIR_NO2,X_KONUMU2,Y_KONUMU2);
      SON_TUR_CENTER(:,11)=[];
      SIRA=SON_TUR_CENTER;
      
          i1=SIRA(1);
          i2=SIRA(2);
          i3=SIRA(3);
          i4=SIRA(4);
          i5=SIRA(5);
          i6=SIRA(6);
          i7=SIRA(7);
          i8=SIRA(8);
          i9=SIRA(9);
          i10=SIRA(10);
          
          MXx12=(MX(i1,1)+MX(i2,1))/2;
          MXy12=(MX(i1,2)+MX(i2,2))/2;
          
          MXx23=(MX(i2,1)+MX(i3,1))/2;
          MXy23=(MX(i2,2)+MX(i3,2))/2;
          
          MXx34=(MX(i3,1)+MX(i4,1))/2;
          MXy34=(MX(i3,2)+MX(i4,2))/2;
          
          MXx45=(MX(i4,1)+MX(i5,1))/2;
          MXy45=(MX(i4,2)+MX(i5,2))/2;
          
          MXx56=(MX(i5,1)+MX(i6,1))/2;
          MXy56=(MX(i5,2)+MX(i6,2))/2;
          
          MXx67=(MX(i6,1)+MX(i7,1))/2;
          MXy67=(MX(i6,2)+MX(i7,2))/2;
          
          MXx78=(MX(i7,1)+MX(i8,1))/2;
          MXy78=(MX(i7,2)+MX(i8,2))/2;
          
          MXx89=(MX(i8,1)+MX(i9,1))/2;
          MXy89=(MX(i8,2)+MX(i9,2))/2;
          
          MXx910=(MX(i9,1)+MX(i10,1))/2;
          MXy910=(MX(i9,2)+MX(i10,2))/2;
          
          A=[INDEX{i1}];
          B=[INDEX{i2}];
          C=[INDEX{i3}];
          D=[INDEX{i4}];
          E=[INDEX{i5}];
          F=[INDEX{i6}];
          G=[INDEX{i7}];
          H=[INDEX{i8}];
          I=[INDEX{i9}];
          J=[INDEX{i10}];
          
          %%% 1. VE 2. SIRA BAÐLANTI
          FARK1=((abs(data(A,1)'-MXx12))+(abs(data(A,2)'-MXy12)));
          [D1 INDS1]=min(FARK1);
          BAGLA1=A(INDS1);
          FARK2=((abs(data(B,1)'-MXx12))+(abs(data(B,2)'-MXy12)));
          [D2 INDS2]=min(FARK2);
          BAGLA2=B(INDS2);
          ADAYLAR1=[BAGLA1 BAGLA2];
          
          %%% 2. VE 3. SIRA BAÐLANTI
          FARK3=((abs(data(B,1)'-MXx23))+(abs(data(B,2)'-MXy23)));
          [D3 INDS3]=min(FARK3);
          BAGLA3=B(INDS3);
          FARK4=((abs(data(C,1)'-MXx23))+(abs(data(C,2)'-MXy23)));
          [D4 INDS4]=min(FARK4);
          BAGLA4=C(INDS4);
          ADAYLAR2=[BAGLA3 BAGLA4];
          
          %%% 3. VE 4. SIRA BAÐLANTI
          FARK5=((abs(data(C,1)'-MXx34))+(abs(data(C,2)'-MXy34)));
          [D5 INDS5]=min(FARK5);
          BAGLA5=C(INDS5);
          FARK6=((abs(data(D,1)'-MXx34))+(abs(data(D,2)'-MXy34)));
          [D6 INDS6]=min(FARK6);
          BAGLA6=D(INDS6);
          ADAYLAR3=[BAGLA5 BAGLA6];
          
          %%% 4. VE 5. SIRA BAÐLANTI
          FARK7=((abs(data(D,1)'-MXx45))+(abs(data(D,2)'-MXy45)));
          [D7 INDS7]=min(FARK7);
          BAGLA7=D(INDS7);
          FARK8=((abs(data(E,1)'-MXx45))+(abs(data(E,2)'-MXy45)));
          [D8 INDS8]=min(FARK8);
          BAGLA8=E(INDS8);
          ADAYLAR4=[BAGLA7 BAGLA8];
          
          %%% 5. VE 6. SIRA BAÐLANTI
          FARK9=((abs(data(E,1)'-MXx56))+(abs(data(E,2)'-MXy56)));
          [D9 INDS9]=min(FARK9);
          BAGLA9=E(INDS9);
          FARK10=((abs(data(F,1)'-MXx56))+(abs(data(F,2)'-MXy56)));
          [D10 INDS10]=min(FARK10);
          BAGLA10=F(INDS10);
          ADAYLAR5=[BAGLA9 BAGLA10];
          
          %%% 6. VE 7. SIRA BAÐLANTI
          FARK11=((abs(data(F,1)'-MXx67))+(abs(data(F,2)'-MXy67)));
          [D11 INDS11]=min(FARK11);
          BAGLA11=F(INDS11);
          FARK12=((abs(data(G,1)'-MXx67))+(abs(data(G,2)'-MXy67)));
          [D12 INDS12]=min(FARK12);
          BAGLA12=G(INDS12);
          ADAYLAR6=[BAGLA11 BAGLA12];
          
          %%% 7. VE 8. SIRA BAÐLANTI
          FARK13=((abs(data(G,1)'-MXx78))+(abs(data(G,2)'-MXy78)));
          [D13 INDS13]=min(FARK13);
          BAGLA13=G(INDS13);
          FARK14=((abs(data(H,1)'-MXx78))+(abs(data(H,2)'-MXy78)));
          [D14 INDS14]=min(FARK14);
          BAGLA14=H(INDS14);
          ADAYLAR7=[BAGLA13 BAGLA14];
          
          %%% 8. VE 9. SIRA BAÐLANTI
          FARK15=((abs(data(H,1)'-MXx89))+(abs(data(H,2)'-MXy89)));
          [D15 INDS15]=min(FARK15);
          BAGLA15=H(INDS15);
          FARK16=((abs(data(I,1)'-MXx89))+(abs(data(I,2)'-MXy89)));
          [D16 INDS16]=min(FARK16);
          BAGLA16=I(INDS16);
          ADAYLAR8=[BAGLA15 BAGLA16];
          
          %%% 9. VE 10. SIRA BAÐLANTI
          FARK17=((abs(data(I,1)'-MXx910))+(abs(data(I,2)'-MXy910)));
          [D17 INDS17]=min(FARK17);
          BAGLA17=I(INDS17);
          FARK18=((abs(data(J,1)'-MXx910))+(abs(data(J,2)'-MXy910)));
          [D18 INDS18]=min(FARK18);
          BAGLA18=J(INDS18);
          ADAYLAR9=[BAGLA17 BAGLA18];
          
          
          SEHIR_NO1=A;
          X_KONUMU1=data(A,1);
          Y_KONUMU1=data(A,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL1=calc;
          GBEST1=single(G_izle);
          TUR_A=SEHIR_NO1(SON_TUR);
          SHIFT1=find(TUR_A==BAGLA1);
          ROTA1=(circshift(TUR_A',numel(TUR_A)-SHIFT1))'; % BAÐLANTI noktasý SONA taþýndý
          
          SEHIR_NO1=B;
          X_KONUMU1=data(B,1);
          Y_KONUMU1=data(B,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL2=calc;
          GBEST2=single(G_izle);
          TUR_B=SEHIR_NO1(SON_TUR);
          SHIFT2=find(TUR_B==BAGLA2);
          ROTA2=(circshift(TUR_B',numel(TUR_B)-SHIFT2+1))';% BAÐLANTI noktasý BAÞA taþýndý
          
          ROTA12=[ROTA1 ROTA2];
          
          SEHIR_NO1=C;
          X_KONUMU1=data(C,1);
          Y_KONUMU1=data(C,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL3=calc;
          GBEST3=single(G_izle);
          TUR_C=SEHIR_NO1(SON_TUR);
          SHIFT3=find(TUR_C==BAGLA4);
          ROTA3=(circshift(TUR_C',numel(TUR_C)-SHIFT3+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT4=find(ROTA12==BAGLA3);
          ROTA_12_SON=(circshift(ROTA12',numel(ROTA12)-SHIFT4))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123=[ROTA_12_SON ROTA3];
          
          
          SEHIR_NO1=D;
          X_KONUMU1=data(D,1);
          Y_KONUMU1=data(D,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL4=calc;
          GBEST4=single(G_izle);
          TUR_D=SEHIR_NO1(SON_TUR);
          SHIFT5=find(TUR_D==BAGLA6);
          ROTA4=(circshift(TUR_D',numel(TUR_D)-SHIFT5+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT6=find(ROTA123==BAGLA5);
          ROTA_123_SON=(circshift(ROTA123',numel(ROTA123)-SHIFT6))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234=[ROTA_123_SON ROTA4];
          
          SEHIR_NO1=E;
          X_KONUMU1=data(E,1);
          Y_KONUMU1=data(E,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL5=calc;
          GBEST5=single(G_izle);
          TUR_E=SEHIR_NO1(SON_TUR);
          SHIFT7=find(TUR_E==BAGLA8);
          ROTA5=(circshift(TUR_E',numel(TUR_E)-SHIFT7+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT8=find(ROTA1234==BAGLA7);
          ROTA_1234_SON=(circshift(ROTA1234',numel(ROTA1234)-SHIFT8))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345=[ROTA_1234_SON ROTA5];
          
          SEHIR_NO1=F;
          X_KONUMU1=data(F,1);
          Y_KONUMU1=data(F,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL6=calc;
          GBEST6=single(G_izle);
          TUR_F=SEHIR_NO1(SON_TUR);
          SHIFT9=find(TUR_F==BAGLA10);
          ROTA6=(circshift(TUR_F',numel(TUR_F)-SHIFT9+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT10=find(ROTA12345==BAGLA9);
          ROTA_12345_SON=(circshift(ROTA12345',numel(ROTA12345)-SHIFT10))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123456=[ROTA_12345_SON ROTA6];
          
          SEHIR_NO1=G;
          X_KONUMU1=data(G,1);
          Y_KONUMU1=data(G,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL7=calc;
          GBEST7=single(G_izle);
          TUR_G=SEHIR_NO1(SON_TUR);
          SHIFT11=find(TUR_G==BAGLA12);
          ROTA7=(circshift(TUR_G',numel(TUR_G)-SHIFT11+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT12=find(ROTA123456==BAGLA11);
          ROTA_123456_SON=(circshift(ROTA123456',numel(ROTA123456)-SHIFT12))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA1234567=[ROTA_123456_SON ROTA7];
          
          SEHIR_NO1=H;
          X_KONUMU1=data(H,1);
          Y_KONUMU1=data(H,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL8=calc;
          GBEST8=single(G_izle);
          TUR_H=SEHIR_NO1(SON_TUR);
          SHIFT13=find(TUR_H==BAGLA14);
          ROTA8=(circshift(TUR_H',numel(TUR_H)-SHIFT13+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT14=find(ROTA1234567==BAGLA13);
          ROTA_1234567_SON=(circshift(ROTA1234567',numel(ROTA1234567)-SHIFT14))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345678=[ROTA_1234567_SON ROTA8];
          
          SEHIR_NO1=I;
          X_KONUMU1=data(I,1);
          Y_KONUMU1=data(I,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL9=calc;
          GBEST9=single(G_izle);
          TUR_I=SEHIR_NO1(SON_TUR);
          SHIFT15=find(TUR_I==BAGLA16);
          ROTA9=(circshift(TUR_I',numel(TUR_I)-SHIFT15+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT16=find(ROTA12345678==BAGLA15);
          ROTA_12345678_SON=(circshift(ROTA12345678',numel(ROTA12345678)-SHIFT16))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA123456789=[ROTA_12345678_SON ROTA9];
          
          SEHIR_NO1=J;
          X_KONUMU1=data(J,1);
          Y_KONUMU1=data(J,2);
          [calc SON_TUR G_izle]=TSPorjFUN(SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
          CL10=calc;
          GBEST10=single(G_izle);
          TUR_J=SEHIR_NO1(SON_TUR);
          SHIFT17=find(TUR_J==BAGLA18);
          ROTA10=(circshift(TUR_J',numel(TUR_J)-SHIFT17+1))';% BAÐLANTI noktasý BAÞA taþýndý
          SHIFT18=find(ROTA123456789==BAGLA17);
          ROTA_123456789_SON=(circshift(ROTA123456789',numel(ROTA123456789)-SHIFT18))'; % BAÐLANTI noktasý SONA taþýndý
          
          ROTA12345678910=[ROTA_123456789_SON ROTA10];
          
          
      CL=CL1+CL2+CL3+CL4+CL5+CL6+CL7+CL8+CL9+CL10;
      
      SEHIR_NO_FCM1=SEHIR_NO_FCM';
      X_KONUMU_FCM1=X_KONUMU_FCM';
      Y_KONUMU_FCM1=Y_KONUMU_FCM';
          
      BIRLESIKTUR=[ROTA12345678910 ROTA12345678910(1)];
      [UZUNLUK]=FCMROTA(SEHIR_NO_FCM1,X_KONUMU_FCM1,Y_KONUMU_FCM1,BIRLESIKTUR);

%       plot(data(ADAYLAR1,1), data(ADAYLAR1,2),'s');
%       plot(data(ADAYLAR2,1), data(ADAYLAR2,2),'s');
%       plot(data(ADAYLAR3,1), data(ADAYLAR3,2),'s');
%       plot(data(ADAYLAR4,1), data(ADAYLAR4,2),'s');
%       plot(data(ADAYLAR5,1), data(ADAYLAR5,2),'s');
%       plot(data(ADAYLAR6,1), data(ADAYLAR6,2),'s');
%       plot(data(ADAYLAR7,1), data(ADAYLAR7,2),'s');
%       plot(data(ADAYLAR8,1), data(ADAYLAR8,2),'s');
%       plot(data(ADAYLAR9,1), data(ADAYLAR9,2),'s');
%       plot(data(index1,1),data(index1,2),'*','color',col(1,:));
%       plot(data(index2,1),data(index2,2),'*','color',col(2,:));
%       plot(data(index3,1),data(index3,2),'*','color',col(3,:));
%       plot(data(index4,1),data(index4,2),'*','color',col(4,:));
%       plot(data(index5,1),data(index5,2),'*','color',col(5,:));
%       plot(data(index6,1),data(index6,2),'*','color',col(6,:));
%       plot(data(index7,1),data(index7,2),'*','color',col(7,:));
%       plot(data(index8,1),data(index8,2),'*','color',col(8,:));
%       plot(data(index9,1),data(index9,2),'*','color',col(9,:));
%       plot(data(index10,1),data(index10,2),'*','color',col(10,:));
%       BIRLESIKTUR
%       UZUNLUK
      
  
end

uzunluk_deney(DENEY)=UZUNLUK;
sayaccluster
sayacdeney=sayacdeney+1
save TOPLU.mat;
end
TOPLU(GENEL,:)=uzunluk_deney;
sayaccluster=sayaccluster+1
end