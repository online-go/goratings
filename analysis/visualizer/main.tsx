import * as React from "react";
import { useState } from "react";
import * as ReactDOM from "react-dom";
import analysis_data from "./data.json";
import { storageGet, storageSet, rankString, humanNumber } from "./util";
import './main.css';

import {
  //LineChart,
    Line,
    ComposedChart,
    Bar,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ReferenceLine,
} from 'recharts';

const ALL = 999;
let data:any = analysis_data;
let ordered_data:Array<any> = Object.keys(data).map(key => data[key]);
ordered_data.sort((a,b) => {
    return b.timestamp - a.timestamp;
});


interface Dataset {
    info: ParsedDatasetName;

    winrate: Array<{
        label:string,
        winrate: number,
        samples: number,
    }>;

    players: Array<{
        label:string,
        count: number,
    }>;

    avg_winrate: number;
}

interface ParsedDatasetName {
    name: string;
    dataset: string;
    num_samples: number;
    ignored: number;
    rating_system: string;

    log_args?: {
        a: number;
        c: number;
    }
    linear_args?: {
        m: number;
        b: number;
    }
}


function processDataSet(name: string, sizes:Array<number>, speeds:Array<number>, handicaps:Array<number>):Dataset {
    let ret:Dataset = {
        info: parseDatasetName(name),
        winrate: [],
        players: [],
        avg_winrate: 0,
    };

    if (sizes.length === 0) {
        sizes = [ALL];
    }
    if (speeds.length === 0) {
        speeds = [ALL];
    }
    if (handicaps.length === 0) {
        handicaps = [ALL];
    }


    for (let rank=0; rank < 40; ++rank) {
        ret.winrate.push({
            label: rankString(rank),
            winrate: 0,
            samples: 0,
        });
    }

    let sample_total = 0;

    console.log(sizes, speeds, handicaps);

    for (let size of sizes) {
        for (let speed of speeds) {
            for (let handicap of handicaps) {
                for (let rank=0; rank < 40; ++rank) {
                    if (data[name]?.black_wins[size] && data[name].black_wins[size][speed]) {
                        if (rank in data[name].black_wins[size][speed]) {
                            ret.winrate[rank].winrate += data[name].black_wins[size][speed][rank][handicap];
                            ret.winrate[rank].samples += data[name].count[size][speed][rank][handicap];
                            sample_total += data[name].count[size][speed][rank][handicap];
                        }
                    }
                }

            }
        }
    }

    let avg_winrate = 0;

    for (let rank=0; rank < 40; ++rank) {
        if (ret.winrate[rank].samples > 0) {
            avg_winrate += ret.winrate[rank].winrate;
            ret.winrate[rank].winrate /= ret.winrate[rank].samples;
        }
    }

    ret.info.num_samples = sample_total;
    ret.info.ignored = data[name].ignored;
    ret.avg_winrate = avg_winrate / sample_total;

    return ret;
}

function getLatestDatasetName():string {
    let ret = "";
    let last = 0;
    for (let name in data) {
        if (data[name].timestamp > last) {
            ret = name;
            last = data[name].timestamp;
        }
    }
    console.log("Latset dataset: ", ret);
    return ret;
}

function parseDatasetName(name: string):ParsedDatasetName {
    let components = name.split(":");

    let ret:ParsedDatasetName = {
        name:  components[0],
        dataset: components[1],
        num_samples: parseInt(components[2]),
        rating_system: components[3],
        ignored: 0,
    };

    switch (ret.rating_system) {
        case 'log':
            ret.log_args = {
                a: parseFloat(components[4]),
                c: parseFloat(components[5]),
            };
            break;

        case 'linear':
            ret.linear_args = {
                b: parseFloat(components[4]),
                m: parseFloat(components[5]),
            };
            break;

        case 'gor':
            break;

        default:
            console.error("Unhandled rating system ", ret.rating_system);
            break;
    }

    return ret;
}


ReactDOM.render(<Main />, document.getElementById("main-content"));

function Main(props:{}):JSX.Element {
    let [size_speed_handicap, _set_ssh]:[SizeSpeedHandicapSelectorState, (s:SizeSpeedHandicapSelectorState) => void] =
        useState(storageGet('sizes_speeds_handicaps', {
            sizes: [],
            speeds: [],
            handicaps: [],
        }));
    let [datasets, _set_datasets]:[Array<string>, (s:Array<string>) => void] =
        useState(storageGet('selected_datasets', [getLatestDatasetName()]));
    let [ct, setCt]:[number, (x:number) => void] = useState(1);


    const set_ssh = (v:SizeSpeedHandicapSelectorState):void => {
        storageSet('sizes_speeds_handicaps', v);
        _set_ssh(v);
        setCt(ct + 1);
        console.log("Should have refreshed");
    }

    const set_datasets = (ev:React.ChangeEvent<HTMLSelectElement>):void => {
        let options = ev.target.options;
        let value = [];
        for (var i = 0, l = options.length; i < l; i++) {
            if (options[i].selected) {
                value.push(options[i].value);
            }
        }
        console.log(value);

        storageSet('selected_datasets', value);
        _set_datasets(value);
    }


    //let latest = processDataSet(getLatestDatasetName());

    return (
        <div id='Main'>
            <div className='configuration'>
                <select multiple={true} value={datasets} onChange={set_datasets}>
                    {ordered_data.map(d => <option key={d.name} value={d.name}>{d.name}</option>)}
                </select>

                <SizeSpeedHandicapSelector state={size_speed_handicap} onChange={set_ssh} />
            </div>

            <div className='StatsContainer'>
                {datasets.map(name => {
                    let dataset = processDataSet(
                        name,
                        size_speed_handicap.sizes,
                        size_speed_handicap.speeds,
                        size_speed_handicap.handicaps,
                    )
                    console.log("hmm");
                    return <Stats key={name} dataset={dataset} />;
                })}
            </div>
        </div>
    );
}


function DataSetDescription(props:{parsed: ParsedDatasetName}):JSX.Element {
    const dsn = props.parsed;


    return (
        <div className='DataSetDescription'>
            <h3>{dsn.name.replace(/[-]/g, " ")}</h3>
            <div>
                <b>Dataset:</b> {dsn.dataset}
                <b>Rating system</b>: {dsn.rating_system}
                {dsn.log_args && <span><b>A:</b> {dsn.log_args.a}</span>}
                {dsn.log_args && <span><b>C:</b> {dsn.log_args.c}</span>}
                {dsn.linear_args && <span><b>M:</b> {dsn.linear_args.m}</span>}
                {dsn.linear_args && <span><b>B:</b> {dsn.linear_args.b}</span>}
            </div>
            <div>
                <b>Samples:</b> {humanNumber(dsn.num_samples)}
                <b>Dropped games:</b> {humanNumber(dsn.ignored)}
            </div>
        </div>
    );

}




interface SizeSpeedHandicapSelectorState {
    sizes: Array<number>;
    speeds: Array<number>;
    handicaps: Array<number>;
}


function SizeSpeedHandicapSelector({state, onChange}
    :{
        state: SizeSpeedHandicapSelectorState,
        onChange: (s:SizeSpeedHandicapSelectorState) => void
    }):JSX.Element
{

    function opt(name: string, index: 'sizes' | 'speeds' | 'handicaps', value:number):JSX.Element {
        let [checked, setChecked] = useState(state[index].indexOf(value) >= 0);

        let input_name = `${index}-${value}`;


        return (
            <dd>
                <input type='checkbox' name={input_name} checked={checked} onChange={(ev) => {
                    if (ev.target.checked) {
                        if (state[index].indexOf(value) < 0) {
                            state[index].push(value);
                        }
                    }
                    else {
                        if (state[index].indexOf(value) >= 0) {
                            state[index].splice(state[index].indexOf(value), 1);
                        }
                    }
                    console.log(state);
                    onChange(state);
                    setChecked(ev.target.checked);
                }} />
                <label htmlFor={input_name}>{name}</label>
            </dd>
        );
    }

    return (
        <div className='SizeSpeedHandicapSelector'>
            <dl>
                <dt>Sizes</dt>
                {opt("9x9", "sizes", 9)}
                {opt("13x13", "sizes", 13)}
                {opt("19x19", "sizes", 19)}
            </dl>

            <dl>
                <dt>Speeds</dt>
                {opt("Blitz", "speeds", 1)}
                {opt("Live", "speeds", 2)}
                {opt("Correspondence", "speeds", 3)}
            </dl>
            <dl>
                <dt>Handicap</dt>
                {opt("0", "handicaps", 0)}
                {opt("1", "handicaps", 1)}
                {opt("2", "handicaps", 2)}
                {opt("3", "handicaps", 3)}
                {opt("4", "handicaps", 4)}
            </dl>
            <dl>
                <dt>&nbsp;</dt>
                {opt("5", "handicaps", 5)}
                {opt("6", "handicaps", 6)}
                {opt("7", "handicaps", 7)}
                {opt("8", "handicaps", 8)}
                {opt("9", "handicaps", 9)}
            </dl>
        </div>
    );
}



function Stats({dataset}:{dataset: Dataset}):JSX.Element {

    return (
        <div className='Stats'>
            <DataSetDescription parsed={dataset.info} />

            <h5>Black Win Rate: {(dataset.avg_winrate * 100).toFixed(1)}%</h5>

            <ComposedChart
                width={500}
                height={300}
                data={dataset.winrate}
                margin={{
                    top: 20, right: 50, left: 20, bottom: 5,
                }}
                >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis tickFormatter={(v:any) => dataset.winrate[v].label} />
                <YAxis domain={[0,100]} tickFormatter={(v:number) => `${v}%`} />

                <Tooltip
                    labelFormatter={(v:any) => rankString(v)}
                    filterNull={true}
                    formatter={(v, name, props) => {
                        if (name === "insufficient data") {
                            return v ? 'yes' : 'no';
                        }

                        if (name === "Samples") {
                            return `${v}%  [${humanNumber((v as number / 100) * dataset.info.num_samples)}]`;
                        }

                        return `${v}%`;
                    }}
                />
                <Legend />
                <ReferenceLine x="Page C" stroke="red" label="Max PV PAGE" />
                <ReferenceLine y={dataset.avg_winrate * 100} stroke="blue" />
                <Line name="Black win rate" type="monotone" dataKey={(e => parseFloat((e.winrate * 100.0).toFixed(2)))} stroke="#8884d8" />
                <Bar name="Samples" dataKey={(e => parseFloat((e.samples * 100.0 / dataset.info.num_samples).toFixed(2)))} fill="#82ca9d" />
                <Area legendType="none" type="step" stroke = "#cccccc" fill="#cccccc"
                    name="insufficient data"
                    dataKey={(e =>
                        (e.samples / dataset.info.num_samples) > 0.01 || e.samples > 100 ? 0 : 100)
                    }
                    />
            </ComposedChart>
        </div>
    );

}
