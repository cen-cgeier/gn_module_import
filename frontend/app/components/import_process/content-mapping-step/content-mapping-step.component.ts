import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FormControl, FormGroup, FormBuilder } from '@angular/forms';
import { StepsService, Step3Data, Step4Data } from '../steps.service';
import { DataService } from '../../../services/data.service';
import { ContentMappingService } from '../../../services/mappings/content-mapping.service';
import { ToastrService } from 'ngx-toastr';
import { ModuleConfig } from '../../../module.config';

@Component({
	selector: 'content-mapping-step',
	styleUrls: [ 'content-mapping-step.component.scss' ],
	templateUrl: 'content-mapping-step.component.html'
})
export class ContentMappingStepComponent implements OnInit, OnChanges {

	public isCollapsed = false;
	public userContentMapping;
	public newMapping: boolean = false;
	public id_mapping;
	public columns;
	public spinner: boolean = false;
	contentTargetForm: FormGroup;
	public contentMappingForm: FormGroup;
	showForm: boolean = false;
	contentMapRes: any;
	stepData: Step3Data;
	//userNomenc = [];
	public nomencName;
	public idInfo;
    public disabled: boolean = true;

	constructor(
        private stepService: StepsService, 
        private _fb: FormBuilder,
        private _ds: DataService,
        private _cm: ContentMappingService,
		private toastr: ToastrService,
		private _router: Router
        ) {}


	ngOnInit() {
		this.stepData = this.stepService.getStepData(3);

		this.contentMappingForm = this._fb.group({
			contentMapping: [ null ],
			mappingName: [ '' ]
		});
		this.contentTargetForm = this._fb.group({});

		// show list of user mappings
		this._cm.getMappingNamesList('content', this.stepData.importId);

        // generate form
        /*
		if (this.stepData.contentMappingInfo) {
			this.generateContentForm();
        }
        */

		this.getNomencInf();

		// listen to change on contentMappingForm select
		this.onMappingName();

		// fill the form
		if (this.stepData.id_content_mapping) {
			this.contentMappingForm.controls['contentMapping'].setValue(this.stepData.id_content_mapping);
			this.fillMapping(this.stepData.id_content_mapping);
		}

	}


	getNomencInf() {
		console.log(this.stepData.table_name);
		this._ds.getNomencInfo(this.stepData.importId).subscribe(
			(res) => {
				console.log(res);		
                this.stepData.contentMappingInfo = res['content_mapping_info'];
                console.log(this.stepData.contentMappingInfo);
                this.generateContentForm();
            },
            (error) => {
                if (error.statusText === 'Unknown Error') {
                    // show error message if no connexion
                    this.toastr.error('ERROR: IMPOSSIBLE TO CONNECT TO SERVER (check your connexion)');
                } else {
                    // show error message if other server error
                    console.log(error);
                    this.toastr.error(error.error.message);
                }
            }
        );
	}


    generateContentForm() {
        console.log(this.stepData.contentMappingInfo);
		this.stepData.contentMappingInfo.forEach(
			(ele) => {
				ele['nomenc_values_def'].forEach(
					(nomenc) => {
						this.contentTargetForm.addControl(nomenc.id, new FormControl(''));
					});
            });
        console.log(this.contentTargetForm);
		this.showForm = true;
    }
	

	onSelectChange(selectedVal, group, formControlName) {
		this.stepData.contentMappingInfo.map(
			(ele) => {
				if (ele.nomenc_abbr === group.nomenc_abbr) {
					ele.user_values.values = ele.user_values.values.filter(
						(value) => {
							return value.id != selectedVal.id;
						}
					);
				}
			}
		);
	}


	onSelectDelete(deletedVal, group, formControlName) {
		console.log(deletedVal);
		console.log(group);
		console.log(formControlName);
		console.log(this.stepData.contentMappingInfo);

		this.stepData.contentMappingInfo.map(
			(ele) => {
				console.log(ele);
				if (ele.nomenc_abbr === group.nomenc_abbr) {
					let temp_array = ele.user_values.values;
					temp_array.push(deletedVal);
					ele.user_values.values = temp_array.slice(0);
				}
			});

		// modify contentTargetForm control values
		let values = this.contentTargetForm.controls[formControlName].value;
		values = values.filter(
			(value) => {
				console.log(value);
				return value.id != deletedVal.id;
			}
		);
		this.contentTargetForm.controls[formControlName].setValue(values);
	}


	onMappingName(): void {
		this.contentMappingForm.get('contentMapping').valueChanges.subscribe(
			(id_mapping) => {
				if (id_mapping) {
                    this.disabled = false;
                    this.fillMapping(id_mapping);
				} else {
					this.getNomencInf();
                    this.contentTargetForm.reset();
                    this.disabled = true;
                }
			},
			(error) => {
				if (error.statusText === 'Unknown Error') {
					// show error message if no connexion
					this.toastr.error('ERROR: IMPOSSIBLE TO CONNECT TO SERVER (check your connexion)');
				} else {
					console.log(error);
                    this.toastr.error(error.error);
				}
			}
		);
    }
	
	
	getId(userValue, nomencId) {
		this.stepData.contentMappingInfo.forEach(
			(contentMapping) => {
				// find nomenc
				contentMapping.nomenc_values_def.forEach(
					(ele) => {
						if (ele.id == nomencId) {
							this.nomencName = contentMapping.nomenc_abbr;
						}
					}
				);
				// find id in nomenc
				if (contentMapping.nomenc_abbr == this.nomencName) {
					contentMapping.user_values.values.map(
						(value) => {
							if (value.value == userValue) {
								this.idInfo = value.id;
								contentMapping.user_values.values = contentMapping.user_values.values.filter(obj => obj.id !== value.id);
							}
						}
					)
				}
			});
		return this.idInfo
	}


	fillMapping(id_mapping) {
		this.id_mapping = id_mapping;
		this._ds.getMappingContents(id_mapping).subscribe(
			(mappingContents) => {
				this.contentTargetForm.reset();
				console.log(mappingContents);
				if (mappingContents[0] != 'empty') {
					for (let content of mappingContents) {
						let arrayVal: any = [];
						for (let val of content) {
							console.log(val);
							if (val['source_value'] != '') {
								let id_info = this.getId(val['source_value'], val['id_target_value']);
								arrayVal.push({id: id_info, value: val['source_value']});
							}
						}
						console.log(arrayVal);
						console.log(content);
						this.contentTargetForm.get(String(content[0]['id_target_value'])).setValue(arrayVal);
					}
				} else {
					this.contentTargetForm.reset();
				}
			},
			(error) => {
				if (error.statusText === 'Unknown Error') {
					// show error message if no connexion
					this.toastr.error('ERROR: IMPOSSIBLE TO CONNECT TO SERVER (check your connexion)');
				} else {
					this.toastr.error(error.error.message);
				}
			}
		);
	}


	onStepBack() {
		this._router.navigate([ `${ModuleConfig.MODULE_URL}/process/step/2` ]);
	}


	onContentMapping(value) {
		// post content mapping form values and fill t_mapping_values table
		this.id_mapping = this.contentMappingForm.get('contentMapping').value;
		this.spinner = true;
		this._ds
			.postContentMap(
				value,
				this.stepData.table_name,
				//this.stepData.selected_columns,
				this.stepData.importId,
				this.id_mapping
			)
			.subscribe(
				(res) => {
					this.contentMapRes = res;
					let step4Data: Step4Data = {
						importId: this.stepData.importId,
						//selected_columns: this.stepData.selected_columns,
						//added_columns: this.stepData.added_columns
					};
				
					let step3Data: Step3Data = this.stepData;
					step3Data.id_content_mapping = this.id_mapping;
					this.stepService.setStepData(3, step3Data);
					this.stepService.setStepData(4, step4Data);

					this._router.navigate([ `${ModuleConfig.MODULE_URL}/process/step/4` ]);
					this.spinner = false;
				},
				(error) => {
					this.spinner = false;
					if (error.statusText === 'Unknown Error') {
						// show error message if no connexion
						this.toastr.error('ERROR: IMPOSSIBLE TO CONNECT TO SERVER (check your connexion)');
					} else {
						// show error message if other server error
						console.log(error);
						this.toastr.error(error.error.message);
					}
				}
			);
	}
    
}
