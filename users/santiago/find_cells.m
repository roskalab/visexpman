function rois=find_cells(rawdata, K, tau, p, merge_thr)
%clear all
%startupShort;
%common_filepath = 'D:\Raw Microscopy Data\Santiago (Test Data) - V2\No smear\716-18d-vivo-m1-reg4-rep1-LGN\';
% common_filepath = 'D:\Raw Microscopy Data\Santiago (Test Data) - V2\More smear\716-18d-vivo-m1-reg3-rep1-LGN-2levels\';
% common_filepath = 'D:\Raw Microscopy Data\Santiago (Test Data) - V2\A little bit of smear\716-18d-vivo-m1-reg2-rep1-LGN\';
%file_structure = '716';
%file_structure = strcat(file_structure,'*');
%cd(common_filepath)
%allFiles = dir(file_structure);
%temp = imread(allFiles(1).name);
%rawdata = zeros(size(temp,1),size(temp,2),size(allFiles,1));
%for i = 1:size(allFiles,1)
%    ct = size(allFiles,1)-(i-1);
%    temp = imread(allFiles(ct).name);
%    if sum(sum(temp==255)) > 255*2
%       rawdata(:,:,ct) = [];
%    else
%        rawdata(:,:,ct) = double(temp);
%    end
%end
%%
% figure;
% imagesc(mean(rawdata,3))
% drawnow
% pause
% figure;
% imagesc(max(rawdata,[],3))
% drawnow
% pause
%% load file
% close all
%addpath(genpath('utilities'));
Y = double(rawdata);
[d1,d2,T] = size(Y);                                % dimensions of dataset
d = d1*d2;                                          % total number of pixels
%% Set parameters
%K = 100;                                          % number of components to be found
%tau = 3;                                          % std of gaussian kernel (size of neuron)
%p = 1;                                            % order of autoregressive system (p = 0 no dynamics, p=1 just decay, p = 2, both rise and decay)
%merge_thr = 0.8;                                  % merging threshold
options = CNMFSetParms(...                     
    'd1',d1,'d2',d2,...                         % dimensions of datasets
    'search_method','dilate','dist',3,...       % search locations when updating spatial components
    'deconv_method','constrained_foopsi',...    % activity deconvolution method
    'temporal_iter',2,...                       % number of block-coordinate descent steps
    'fudge_factor',0.98,...                     % bias correction for AR coefficients
    'merge_thr',merge_thr,...                    % merging threshold
    'gSig',tau...
    );
%% Data pre-processing
[P,Y] = preprocess_data(Y,p);
%% fast initialization of spatial components using greedyROI and HALS
[Ain,Cin,bin,fin,center] = initialize_components(Y,K,tau,options,P);  % initialize
% display centers of found components
Cn =  correlation_image(Y); %reshape(P.sn,d1,d2);  %max(Y,[],3); %std(Y,[],3); % image statistic (only for display purposes)
%figure;imagesc(Cn);
%    axis equal; axis tight; hold all;
%    scatter(center(:,2),center(:,1),'mo');
%    title('Center of ROIs found from initialization algorithm');
%    drawnow;
%% manually refine components (optional)
refine_components = false;  % flag for manual refinement
if refine_components
    [Ain,Cin,center] = manually_refine_components(Y,Ain,Cin,center,Cn,tau,options);
end
% close all
   
%% update spatial components
Yr = reshape(Y,d,T);
[A,b,Cin] = update_spatial_components(Yr,Cin,fin,[Ain,bin],P,options);
%% update temporal components
P.p = 0;    % set AR temporarily to zero for speed
[C,f,P,S,YrA] = update_temporal_components(Yr,A,b,Cin,fin,P,options);
%% classify components
[ROIvars.rval_space,ROIvars.rval_time,ROIvars.max_pr,ROIvars.sizeA,keep] = classify_components(Y,A,C,b,f,YrA,options);
A_keep = A(:,keep);
C_keep = C(keep,:);
%% merge found components
[Am,Cm,K_m,merged_ROIs,Pm,Sm] = merge_components(Yr,A_keep,b,C_keep,f,P,S,options);
%% refine estimates excluding rejected components
Pm.p = p;    % restore AR value
[A2,b2,C2] = update_spatial_components(Yr,Cm,f,[Am,b],Pm,options);
[C2,f2,P2,S2,YrA2] = update_temporal_components(Yr,A2,b2,C2,f,Pm,options);
%% do some plotting
[A_or,C_or,S_or,P_or] = order_ROIs(A2,C2,S2,P2); % order components
K_m = size(C_or,1);
[C_df,~] = extract_DF_F(Yr,A_or,C_or,P_or,options); % extract DF/F values (optional)
%figure;
%[Coor,json_file] = plot_contours(A_or,Cn,options,1); % contour plot of spatial footprints
%savejson('jmesh',json_file,'filename');        % optional save json file with component coordinates (requires matlab json library)
%% Store a location variable
roiLoc = zeros(size(rawdata,1),size(rawdata,2),size(A_or,2));
for i = 1:size(A_or,2)
    roiLoc(:,:,i) = full(reshape(A_or(:,i),size(rawdata,1),size(rawdata,2)));
end
%figure;
%ax1 = axes;
%image(mean(rawdata,3));   
%axis equal tight
%ax2 = axes;
% A = zeros(size(rawdata,1),size(rawdata,2),3);
% for i = 1:size(roiLoc,3)
%     colorChoice = randn(1,3);
%     %A = cat(3,cat(3,roiLoc(:,:,i)/max(max(roiLoc(:,:,i)))*colorChoice(1,1),roiLoc(:,:,i)/max(max(roiLoc(:,:,i)))*colorChoice(1,2)),roiLoc(:,:,i)/max(max(roiLoc(:,:,i)))*colorChoice(1,3));
%     A = A + cat(3,cat(3,(roiLoc(:,:,i)>0.1)*colorChoice(1,1),(roiLoc(:,:,i)>0.1)*colorChoice(1,2)),(roiLoc(:,:,i)>0.1)*colorChoice(1,3));
% end
% hold on
% a = image(permute(A,[1 2 3]));
% set(a,'AlphaData',0.3);
%hold on;
%for i = 1:size(roiLoc,3)
    % contour(roiLoc(:,:,i))
%    contour(roiLoc(:,:,i)/max(max(roiLoc(:,:,i))),[0.25:0.15:0.75])
%end
%axis equal tight
%set(ax2,'ydir','reverse')
%linkaxes([ax1,ax2])
%ax2.Visible = 'off';
%ax2.XTick = [];
%ax2.YTick = [];
%colormap(ax1,'gray')
%colormap(ax2,'hot')
rois=roiLoc;
